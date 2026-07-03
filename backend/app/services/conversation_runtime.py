import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

from app.conversation_engine.brain import CognitiveConversationEngine
from app.conversation_engine.blackboard import BlackboardManager, BlackboardPlan, ConversationBlackboard
from app.knowledge import KnowledgeContextBuilder, KnowledgeSelection
from app.utils import get_logger

logger = get_logger(__name__)


@dataclass
class AIConversationContext:
    conversation_id: str
    memory_before: Dict[str, Any]
    hospital_context: Dict[str, Any]
    campaign_context: Dict[str, Any]
    business_rules: List[str]
    allowed_tools: List[Dict[str, Any]]
    conversation_history: List[Dict[str, Any]]
    current_state: str
    current_patient_message: str
    relevant_knowledge: Optional[KnowledgeSelection]
    blackboard: ConversationBlackboard
    blackboard_plan: BlackboardPlan
    system_prompt: str
    user_prompt: str


class ConversationRuntime:
    """State, context, safety, and persistence for LLM-led conversations.

    This runtime does not choose the next conversational action. It gives the
    LLM the full business context, then validates the result before saving it.
    """

    def __init__(self, knowledge_context_builder: Optional[KnowledgeContextBuilder] = None):
        self.knowledge_context_builder = knowledge_context_builder
        self.blackboard_manager = BlackboardManager()
        self.cognitive_engine = CognitiveConversationEngine()

    def create_session(self, conversation_id: str, client_id: str) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        return {
            "client_id": client_id,
            "created_at": now,
            "last_activity_at": now,
            "messages": [],
            "memory": self.new_memory(),
            "blackboard": self.blackboard_manager.new(conversation_id).to_dict(),
            "conversation_cursor": self.new_cursor(conversation_id),
            "last_tool_results": [],
            "recent_tool_signatures": [],
            "last_ai_context": None,
            "last_validation": None,
            "last_selected_knowledge_files": [],
            "last_cognitive_trace": None,
        }

    def hydrate_session(self, session: Dict[str, Any], conversation_id: str, client_id: str) -> Dict[str, Any]:
        session["client_id"] = session.get("client_id") or client_id
        session.setdefault("created_at", datetime.utcnow().isoformat())
        session["last_activity_at"] = datetime.utcnow().isoformat()
        session.setdefault("messages", [])
        session["memory"] = self.merge_memory(session.get("memory"))
        session["blackboard"] = self.blackboard_manager.hydrate(
            session.get("blackboard"),
            conversation_id,
        ).to_dict()
        session["conversation_cursor"] = self.merge_cursor(
            session.get("conversation_cursor"),
            conversation_id,
            session["memory"].get("current_state", "ACTIVE"),
        )
        session.setdefault("last_tool_results", [])
        session.setdefault("recent_tool_signatures", [])
        session.setdefault("last_cognitive_trace", None)
        return session

    def new_memory(self) -> Dict[str, Any]:
        return {
            "current_state": "ACTIVE",
            "conversation_summary": "",
            "patient_preferences": {},
            "questions_asked": [],
            "questions_answered": [],
            "questions_pending": [],
            "important_facts": {},
            "patient_sentiment": "unknown",
            "patient_interest": "unknown",
            "previous_commitments": [],
            "previous_patient_reply": None,
            "previous_ai_reply": None,
            "known_facts": {},
            "last_tool_results": [],
        }

    def merge_memory(self, memory: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        merged = self.new_memory()
        merged.update(memory or {})
        for key in ["questions_asked", "questions_answered", "questions_pending", "previous_commitments", "last_tool_results"]:
            merged[key] = list(merged.get(key) or [])
        for key in ["patient_preferences", "important_facts", "known_facts"]:
            merged[key] = dict(merged.get(key) or {})
        return merged

    def new_cursor(self, conversation_id: str) -> Dict[str, Any]:
        return {
            "conversation_id": conversation_id,
            "current_node": "ACTIVE",
            "completed": [],
            "completed_nodes": [],
            "last_ai_reply_at": None,
        }

    def merge_cursor(self, cursor: Optional[Dict[str, Any]], conversation_id: str, current_state: str) -> Dict[str, Any]:
        merged = self.new_cursor(conversation_id)
        merged.update(cursor or {})
        completed = merged.get("completed") or merged.get("completed_nodes") or []
        merged["completed"] = list(dict.fromkeys(completed))
        merged["completed_nodes"] = list(dict.fromkeys(completed))
        merged["current_node"] = merged.get("current_node") or current_state
        return merged

    def build_ai_context(
        self,
        conversation_id: str,
        session: Dict[str, Any],
        hospital_context: Dict[str, Any],
        campaign_context: Dict[str, Any],
        business_rules: List[str],
        allowed_tools: List[Dict[str, Any]],
        current_patient_message: str,
    ) -> AIConversationContext:
        memory_before = deepcopy(session["memory"])
        history = deepcopy(session.get("messages", []))
        current_state = memory_before.get("current_state", "ACTIVE")
        blackboard = self.blackboard_manager.hydrate(session.get("blackboard"), conversation_id)
        blackboard_plan = self.blackboard_manager.before_llm(
            blackboard=blackboard,
            patient_message=current_patient_message,
            memory=memory_before,
            current_state=current_state,
        )
        session["blackboard"] = blackboard.to_dict()
        relevant_knowledge = self.build_knowledge_context(
            current_patient_message=current_patient_message,
            memory=memory_before,
            current_state=current_state,
            model=hospital_context.get("model"),
        )
        system_prompt = self.render_system_prompt(
            hospital_context=hospital_context,
            campaign_context=campaign_context,
            memory=memory_before,
            history=history,
            business_rules=business_rules,
            tools=allowed_tools,
            current_state=current_state,
            relevant_knowledge=relevant_knowledge,
            blackboard=blackboard,
            blackboard_plan=blackboard_plan,
        )
        user_prompt = self.render_user_prompt(current_patient_message)
        context = AIConversationContext(
            conversation_id=conversation_id,
            memory_before=memory_before,
            hospital_context=hospital_context,
            campaign_context=campaign_context,
            business_rules=business_rules,
            allowed_tools=allowed_tools,
            conversation_history=history,
            current_state=current_state,
            current_patient_message=current_patient_message,
            relevant_knowledge=relevant_knowledge,
            blackboard=blackboard,
            blackboard_plan=blackboard_plan,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        session["last_ai_context"] = {
            "current_state": current_state,
            "memory_before": memory_before,
            "business_rules": business_rules,
            "tool_names": [tool.get("name") for tool in allowed_tools],
            "selected_knowledge_files": relevant_knowledge.selected_files if relevant_knowledge else [],
            "blackboard": blackboard.to_dict(),
            "blackboard_plan": blackboard_plan.to_dict(),
        }
        session["last_selected_knowledge_files"] = (
            relevant_knowledge.selected_files if relevant_knowledge else []
        )
        self.log_context(context)
        return context

    def build_knowledge_context(
        self,
        current_patient_message: str,
        memory: Dict[str, Any],
        current_state: str,
        model: Optional[str] = None,
    ) -> Optional[KnowledgeSelection]:
        if not self.knowledge_context_builder:
            return None
        return self.knowledge_context_builder.build(
            patient_message=current_patient_message,
            memory=memory,
            conversation_state=current_state,
            detected_intent=memory.get("patient_interest"),
            current_goal=memory.get("current_goal"),
            model=model,
        )

    def render_system_prompt(
        self,
        hospital_context: Dict[str, Any],
        campaign_context: Dict[str, Any],
        memory: Dict[str, Any],
        history: List[Dict[str, Any]],
        business_rules: List[str],
        tools: List[Dict[str, Any]],
        current_state: str,
        relevant_knowledge: Optional[KnowledgeSelection] = None,
        blackboard: Optional[ConversationBlackboard] = None,
        blackboard_plan: Optional[BlackboardPlan] = None,
    ) -> str:
        previous_patient = memory.get("previous_patient_reply") or ""
        previous_ai = memory.get("previous_ai_reply") or ""
        sections = [
            self.xml_section("Hospital", self.to_json(hospital_context)),
            self.xml_section("Campaign", self.to_json(campaign_context)),
            self.xml_section("ConversationMemory", self.to_json(self.compact_memory(memory))),
            (
                self.blackboard_manager.render_prompt_section(blackboard, blackboard_plan)
                if blackboard and blackboard_plan
                else self.xml_section("Blackboard", "")
            ),
            self.xml_section("ConversationHistory", self.to_json(self.compact_history(history[-8:]))),
            relevant_knowledge.prompt_section if relevant_knowledge else self.xml_section("RelevantKnowledge", ""),
            self.xml_section("BusinessRules", self.to_json(business_rules)),
            self.xml_section("Tools", self.to_json(self.compact_tools(tools))),
            self.xml_section("PreviousPatientReply", self.truncate(previous_patient, 320)),
            self.xml_section("PreviousAIReply", self.truncate(previous_ai, 420)),
            self.xml_section("CurrentConversationState", current_state),
            self.xml_section(
                "Task",
                (
                    "Continue the hospital campaign conversation naturally. "
                    "The Blackboard is the working memory and planner decision; obey it exactly. "
                    "If Blackboard planner.must_answer_questions is not empty, answer those pending questions first. "
                    "Do not repeat greeting, campaign, or interest checks listed in Blackboard planner.avoid. "
                    "You only choose natural wording and whether a tool is required; never choose a different next step. "
                    "Respond in natural Telugu or Telugu-English "
                    "matching the patient. Use the context. Do not invent hospital facts. "
                    "Use RelevantKnowledge as the source of truth for identity, hospital, campaign, FAQ, style, and business rules. "
                    "Ask at most one follow-up question. Return only the caller-facing reply. "
                    "Do not return XML, JSON, analysis, memory updates, or section tags."
                ),
            ),
        ]
        return "\n".join(sections)

    def render_user_prompt(self, patient_message: str) -> str:
        return self.xml_section("CurrentPatientMessage", patient_message)

    def compact_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool.get("name"),
                "description": tool.get("description"),
            }
            for tool in tools
        ]

    def compact_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        compact = deepcopy(memory)
        compact["conversation_summary"] = self.truncate(compact.get("conversation_summary") or "", 900)
        compact["previous_patient_reply"] = self.truncate(compact.get("previous_patient_reply") or "", 320)
        compact["previous_ai_reply"] = self.truncate(compact.get("previous_ai_reply") or "", 420)
        compact["last_tool_results"] = compact.get("last_tool_results", [])[-2:]
        return compact

    def compact_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "role": message.get("role"),
                "content": self.truncate(message.get("content") or "", 360),
            }
            for message in history
        ]

    def truncate(self, text: str, limit: int) -> str:
        text = str(text or "")
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def business_rules(self) -> List[str]:
        return [
            "Do not hallucinate hospital location, campaign dates, doctors, prices, or services.",
            "Do not confirm an appointment unless the backend booking tool returns confirmed.",
            "Do not give unsafe medical advice. For urgent symptoms, advise emergency care.",
            "Do not repeat greetings or business questions already visible in memory/history.",
            "Answer the patient's latest question before asking a new one.",
            "Ask at most one follow-up question.",
            "Use tools when availability, booking, patient lookup, or source-of-truth data is required.",
        ]

    def campaign_context(self, client_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "campaign_name": client_context.get("campaign_name") or client_context.get("campaign") or "Hospital campaign",
            "language": client_context.get("language"),
            "goal": client_context.get("goal") or "Continue outreach and help the patient with campaign questions.",
            "known_details": client_context,
        }

    def validate_response(
        self,
        response_text: str,
        context: AIConversationContext,
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        text = (response_text or "").strip()
        lowered = text.lower()
        violations = []
        if not text:
            violations.append("empty response")
        if re.search(r"</?[A-Za-z][^>]*>", text):
            violations.append("xml or structured markup in caller reply")
        if len(re.findall(r"\?", text)) > 1:
            violations.append("more than one follow-up question")
        if self.repeats_previous_reply(text, context.memory_before):
            violations.append("repeated previous ai reply")
        if self.unsafe_medical_advice(lowered):
            violations.append("unsafe medical advice")
        if self.claims_booking_without_tool(lowered, tool_results or []):
            violations.append("appointment confirmation without booking tool")
        if self.possible_hallucinated_hospital_fact(text, context.hospital_context):
            violations.append("possible hallucinated hospital fact")
        violations.extend(self.blackboard_response_violations(text, context))
        if self.conversation_question_ignored(text, context):
            violations.append("conversation question ignored")
        if self.summary_incorrect(text, context):
            violations.append("summary incorrect")
        return {"valid": not violations, "violations": violations}

    def cognitive_review_response(
        self,
        response_text: str,
        session: Dict[str, Any],
        context: AIConversationContext,
    ) -> str:
        plan_dict = {
            "current_state": context.current_state,
            "patient_intent": context.blackboard.last_patient_intent,
            "goal": context.blackboard.current_goal,
            "questions_to_answer": context.blackboard_plan.must_answer_questions,
            "questions_to_ask": [],
            "avoid": context.blackboard_plan.avoid,
            "next_state": context.current_state,
            "close_conversation": context.current_state in {"CLOSING", "FINISHED"},
            "entities": {
                "response_plan": {
                    "knowledge_needed": (
                        context.relevant_knowledge.selected_files
                        if context.relevant_knowledge
                        else []
                    )
                }
            },
            "forbidden_claims": ["unconfirmed venue", "unconfirmed timing", "unconfirmed doctor"],
        }
        thought = self.cognitive_engine.think(session, plan_dict)
        final_text, trace = self.cognitive_engine.finalize_response(
            candidate=response_text,
            session=session,
            policy_plan=plan_dict,
            thought=thought,
        )
        session["last_cognitive_trace"] = trace
        return final_text

    def blackboard_response_violations(self, response_text: str, context: AIConversationContext) -> List[str]:
        violations = []
        lowered = (response_text or "").lower()
        plan = context.blackboard_plan
        if plan.must_answer_questions and "?" in response_text and not self.answers_all_expected_questions(response_text, plan.must_answer_questions):
            violations.append("asked follow-up before resolving pending questions")
        avoid = set(plan.avoid)
        if "repeat_greeting" in avoid and any(token in lowered for token in ["namaskaram", "hello", "hi "]):
            violations.append("repeated greeting despite blackboard")
        if "repeat_campaign" in avoid and lowered.count("camp") > 0 and not plan.must_answer_questions:
            violations.append("repeated campaign despite blackboard")
        if "repeat_interest" in avoid and any(token in lowered for token in ["interest unda", "interested aa"]):
            violations.append("repeated interest despite blackboard")
        return violations

    def conversation_question_ignored(self, response_text: str, context: AIConversationContext) -> bool:
        if context.blackboard_plan.route != "MEMORY_QUERY_ENGINE":
            return False
        expected = (context.blackboard_plan.direct_response or "").strip().lower()
        actual = (response_text or "").strip().lower()
        return bool(expected and expected != actual)

    def summary_incorrect(self, response_text: str, context: AIConversationContext) -> bool:
        if context.blackboard_plan.route != "MEMORY_QUERY_ENGINE":
            return False
        if context.blackboard.last_patient_intent != "ASK_PATIENT_COMMITMENT":
            return False
        committed = bool(context.blackboard.patient_commitments or context.blackboard.interest_confirmed)
        lowered = (response_text or "").lower()
        return committed and not any(token in lowered for token in ["avunu", "yes", "confirm", "chepparu"])

    def answers_all_expected_questions(self, response_text: str, questions: List[str]) -> bool:
        lowered = (response_text or "").lower()
        markers = {
            "identity": ["nenu", "hospital", "maatlad"],
            "purpose": ["call", "invite", "camp"],
            "campaign": ["camp", "check", "medicine", "health"],
            "location": ["venue", "place", "location", "exact place"],
            "time": ["time", "timing", "correct time"],
            "doctor": ["doctor", "hospital team", "guide"],
            "medicine": ["medicine", "mandulu", "doctor check"],
            "fee": ["free", "fee", "check-up"],
            "contact": ["contact", "number", "phone"],
        }
        expected = [question for question in questions if question in markers]
        return all(any(marker in lowered for marker in markers[question]) for question in expected)

    def clean_response_text(self, response_text: str) -> str:
        text = (response_text or "").strip()
        tagged_reply = re.search(
            r"<CurrentAIReply>\s*(.*?)\s*</CurrentAIReply>",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if tagged_reply:
            text = tagged_reply.group(1).strip()
        text = re.sub(r"<(ConversationMemory|Task|ToolResults|ValidationErrors)>.*", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"</?[A-Za-z][^>]*>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def repeats_previous_reply(self, text: str, memory: Dict[str, Any]) -> bool:
        previous = (memory.get("previous_ai_reply") or "").strip().lower()
        return bool(previous and text.strip().lower() == previous)

    def unsafe_medical_advice(self, lowered_text: str) -> bool:
        unsafe_phrases = ["ignore", "no need doctor", "stop medicine", "take double dose"]
        return any(phrase in lowered_text for phrase in unsafe_phrases)

    def claims_booking_without_tool(self, lowered_text: str, tool_results: List[Dict[str, Any]]) -> bool:
        confirms = any(word in lowered_text for word in ["booked", "confirmed", "appointment fix", "appointment confirm"])
        if not confirms:
            return False
        return not any(
            result.get("tool") == "book_appointment"
            and isinstance(result.get("result"), dict)
            and result["result"].get("status") == "confirmed"
            for result in tool_results
        )

    def possible_hallucinated_hospital_fact(self, text: str, hospital_context: Dict[str, Any]) -> bool:
        if not text:
            return False
        known_text = json.dumps(hospital_context, ensure_ascii=True).lower()
        risky_markers = ["address", "location", "venue", "doctor", "price", "fee"]
        mentions_risky_fact = any(marker in text.lower() for marker in risky_markers)
        has_context = any(marker in known_text for marker in risky_markers)
        return mentions_risky_fact and not has_context

    def build_regeneration_prompt(
        self,
        patient_message: str,
        validation: Dict[str, Any],
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        return (
            f"{self.render_user_prompt(patient_message)}\n"
            f"{self.xml_section('ValidationErrors', self.to_json(validation.get('violations', [])))}\n"
            f"{self.xml_section('ToolResults', self.to_json(tool_results or []))}\n"
            "<Task>Regenerate a safer natural reply. Keep the same conversation context and obey the business rules.</Task>"
        )

    def persist_user_turn(self, session: Dict[str, Any], patient_message: str) -> None:
        session["messages"].append({
            "role": "user",
            "content": patient_message,
            "timestamp": datetime.utcnow().isoformat(),
        })
        memory = session["memory"]
        memory["previous_patient_reply"] = patient_message
        self.capture_basic_facts(memory, patient_message)

    def persist_assistant_turn(
        self,
        session: Dict[str, Any],
        response_text: str,
        validation: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
    ) -> None:
        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat(),
            "validation": validation,
            "tool_results": tool_results,
        })
        session["messages"] = session["messages"][-16:]
        memory = session["memory"]
        memory["previous_ai_reply"] = response_text
        memory["last_tool_results"] = tool_results[-6:]
        memory["conversation_summary"] = self.summarize_recent(session["messages"])
        memory["current_state"] = self.derive_state(memory, response_text, validation)
        blackboard = self.blackboard_manager.hydrate(
            session.get("blackboard"),
            session["conversation_cursor"].get("conversation_id"),
        )
        blackboard.current_state = memory["current_state"]
        self.blackboard_manager.after_ai(blackboard, response_text, memory)
        session["blackboard"] = blackboard.to_dict()
        memory["questions_asked"] = list(blackboard.questions_asked)
        memory["questions_answered"] = list(blackboard.questions_answered)
        memory["questions_pending"] = list(blackboard.questions_pending)
        memory["current_goal"] = blackboard.current_goal
        cursor = session["conversation_cursor"]
        cursor["current_node"] = memory["current_state"]
        cursor["last_ai_reply_at"] = datetime.utcnow().isoformat()
        session["last_validation"] = validation
        session["last_activity_at"] = datetime.utcnow().isoformat()

    def persist_tool_results(self, session: Dict[str, Any], tool_results: List[Dict[str, Any]]) -> None:
        if not tool_results:
            return
        session["last_tool_results"] = tool_results[-6:]
        memory = session["memory"]
        memory["last_tool_results"] = tool_results[-6:]
        for tool_result in tool_results:
            result = tool_result.get("result", {})
            if isinstance(result, dict):
                memory["known_facts"].update({
                    key: value
                    for key, value in result.items()
                    if key in {"doctor_name", "date", "time", "available", "status", "message"}
                })

    def capture_basic_facts(self, memory: Dict[str, Any], text: str) -> None:
        phone_match = re.search(r"\b(?:\+91[- ]?)?([6-9]\d{9})\b", text or "")
        if phone_match:
            memory["important_facts"]["phone"] = phone_match.group(1)
        lowered = (text or "").lower()
        if "morning" in lowered or "udayam" in lowered:
            memory["patient_preferences"]["time"] = "morning"
        elif "evening" in lowered or "sayantram" in lowered:
            memory["patient_preferences"]["time"] = "evening"
        if any(token in lowered for token in ["vastanu", "vasthanu", "ostanu", "i will come", "pakka"]):
            if "attend" not in memory["previous_commitments"]:
                memory["previous_commitments"].append("attend")
            memory["patient_interest"] = "confirmed"
            memory["known_facts"]["attendance"] = "confirmed"

    def derive_state(self, memory: Dict[str, Any], response_text: str, validation: Dict[str, Any]) -> str:
        if not validation.get("valid"):
            return "NEEDS_REVIEW"
        lowered = (response_text or "").lower()
        if any(word in lowered for word in ["thank you", "thanks", "bye"]):
            return "CLOSING"
        return "ACTIVE"

    def summarize_recent(self, messages: List[Dict[str, Any]]) -> str:
        recent = messages[-6:]
        parts = []
        for message in recent:
            role = message.get("role")
            content = (message.get("content") or "").strip()
            if content:
                parts.append(f"{role}: {content}")
        return "\n".join(parts)

    def to_json(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"), default=str)

    def xml_section(self, name: str, value: str) -> str:
        return f"<{name}>\n{escape(str(value))}\n</{name}>"

    def log_context(self, context: AIConversationContext) -> None:
        logger.info(
            "AI conversation context built",
            extra={
                "extra_data": {
                    "conversation_id": context.conversation_id,
                    "current_state": context.current_state,
                    "memory_before": context.memory_before,
                    "history_count": len(context.conversation_history),
                    "tool_names": [tool.get("name") for tool in context.allowed_tools],
                    "business_rules_count": len(context.business_rules),
                    "selected_knowledge_files": (
                        context.relevant_knowledge.selected_files
                        if context.relevant_knowledge
                        else []
                    ),
                    "blackboard": context.blackboard.to_dict(),
                    "blackboard_plan": context.blackboard_plan.to_dict(),
                    "knowledge_prompt_size": (
                        context.relevant_knowledge.prompt_size
                        if context.relevant_knowledge
                        else 0
                    ),
                }
            },
        )
