import json
from typing import Any, Dict

from app.conversation_engine.blackboard.blackboard_models import BlackboardPlan, ConversationBlackboard
from app.conversation_engine.blackboard.conversation_goal import ConversationGoalEngine
from app.conversation_engine.blackboard.question_tracker import QuestionTracker
from app.conversation_engine.conversation_intelligence import (
    AnswerAssembler,
    ConversationSummarizer,
    MemoryQueryEngine,
    QuestionDecomposer,
)
from app.utils import get_logger


logger = get_logger(__name__)


class ConversationBlackboardEngine:
    """Working memory that sits before the planner and LLM."""

    def __init__(self):
        self.questions = QuestionTracker()
        self.goals = ConversationGoalEngine()
        self.decomposer = QuestionDecomposer()
        self.memory_queries = MemoryQueryEngine()
        self.answer_assembler = AnswerAssembler()
        self.summarizer = ConversationSummarizer()

    def new(self, conversation_id: str) -> ConversationBlackboard:
        return ConversationBlackboard(conversation_id=conversation_id)

    def hydrate(self, data: Dict[str, Any] | None, conversation_id: str) -> ConversationBlackboard:
        return ConversationBlackboard.from_dict(data, conversation_id)

    def before_llm(
        self,
        blackboard: ConversationBlackboard,
        patient_message: str,
        memory: Dict[str, Any],
        current_state: str,
    ) -> BlackboardPlan:
        blackboard.current_state = current_state
        blackboard.conversation_summary = memory.get("conversation_summary") or blackboard.conversation_summary
        self._sync_flags_from_memory(blackboard, memory)
        self._extract_entities(blackboard, patient_message)
        memory_intent = self.memory_queries.detect(patient_message)
        if memory_intent:
            blackboard.last_patient_intent = memory_intent
            direct_response = self.memory_queries.answer(memory_intent, blackboard=blackboard, memory=memory)
            blackboard.reflection_output = direct_response
            blackboard.conversation_summary = self.summarizer.summarize(blackboard, memory) or blackboard.conversation_summary
            plan = BlackboardPlan(
                current_goal="Answer conversation memory question",
                planner_decision="Route conversation reflection question to Memory Query Engine before LLM.",
                response_goals=["Answer conversation memory question from blackboard"],
                must_answer_questions=[],
                avoid=["do not enter normal dialogue flow"],
                direct_response=direct_response,
                route="MEMORY_QUERY_ENGINE",
            )
            blackboard.current_goal = plan.current_goal
            blackboard.planner_decision = plan.planner_decision
            self.log_debug(blackboard, plan)
            return plan

        intent = self._detect_intent(patient_message)
        blackboard.last_patient_intent = intent

        new_questions = self.decomposer.decompose_keys(patient_message)
        if not new_questions:
            new_questions = self.questions.extract_questions(patient_message)
        asked, answered, pending = self.questions.add_asked(
            blackboard.questions_asked,
            blackboard.questions_answered,
            blackboard.questions_pending,
            new_questions,
        )
        blackboard.questions_asked = asked
        blackboard.questions_answered = answered
        blackboard.questions_pending = pending

        if len(new_questions) > 1:
            direct_response = self.answer_assembler.assemble(
                new_questions,
                context=self._context_from_memory(memory),
                include_follow_up=True,
            )
            plan = BlackboardPlan(
                current_goal="Answer multiple patient questions",
                planner_decision="Route multi-question turn through Question Decomposer and Answer Assembler.",
                response_goals=[f"Answer {question}" for question in new_questions],
                must_answer_questions=list(dict.fromkeys(new_questions)),
                avoid=["do not skip any decomposed question"],
                direct_response=direct_response,
                route="QUESTION_DECOMPOSER",
            )
            blackboard.current_goal = plan.current_goal
            blackboard.planner_decision = plan.planner_decision
            blackboard.conversation_summary = self.summarizer.summarize(blackboard, memory) or blackboard.conversation_summary
            self.log_debug(blackboard, plan)
            return plan

        plan = self.goals.plan(blackboard)
        blackboard.current_goal = plan.current_goal
        blackboard.planner_decision = plan.planner_decision
        blackboard.conversation_summary = self.summarizer.summarize(blackboard, memory) or blackboard.conversation_summary
        self.log_debug(blackboard, plan)
        return plan

    def after_ai(self, blackboard: ConversationBlackboard, ai_reply: str, memory: Dict[str, Any]) -> BlackboardPlan:
        resolved = self.questions.answered_by_response(ai_reply, blackboard.questions_pending)
        blackboard.questions_answered, blackboard.questions_pending = self.questions.resolve(
            blackboard.questions_answered,
            blackboard.questions_pending,
            resolved,
        )
        blackboard.last_ai_action = self._summarize_action(ai_reply)
        blackboard.conversation_summary = memory.get("conversation_summary") or blackboard.conversation_summary
        lowered = (ai_reply or "").lower()
        if "namaskaram" in lowered or "hello" in lowered:
            blackboard.greeting_done = True
        if "camp" in lowered or "campaign" in lowered or "check-up" in lowered or "checkup" in lowered:
            blackboard.campaign_explained = True
        blackboard.conversation_summary = self.summarizer.summarize(blackboard, memory) or blackboard.conversation_summary
        plan = self.goals.plan(blackboard)
        blackboard.current_goal = plan.current_goal
        blackboard.planner_decision = plan.planner_decision
        return plan

    def prompt_payload(self, blackboard: ConversationBlackboard, plan: BlackboardPlan) -> Dict[str, Any]:
        payload = blackboard.to_dict()
        payload["planner"] = plan.to_dict()
        return payload

    def render_prompt_section(self, blackboard: ConversationBlackboard, plan: BlackboardPlan) -> str:
        return "<Blackboard>\n" + json.dumps(self.prompt_payload(blackboard, plan), ensure_ascii=True, separators=(",", ":")) + "\n</Blackboard>"

    def _sync_flags_from_memory(self, blackboard: ConversationBlackboard, memory: Dict[str, Any]) -> None:
        blackboard.interest_confirmed = bool(memory.get("interest_confirmed") or blackboard.interest_confirmed)
        blackboard.callback_requested = bool(memory.get("callback_requested") or blackboard.callback_requested)
        blackboard.appointment_requested = bool(memory.get("appointment_requested") or blackboard.appointment_requested)
        blackboard.greeting_done = bool(memory.get("greeting_done") or blackboard.greeting_done)
        blackboard.campaign_explained = bool(memory.get("campaign_explained") or blackboard.campaign_explained)
        if memory.get("patient_name"):
            blackboard.patient_name = memory["patient_name"]
        blackboard.facts_confirmed.update(memory.get("known_facts") or {})
        blackboard.patient_commitments = list(dict.fromkeys(
            blackboard.patient_commitments + list(memory.get("previous_commitments") or [])
        ))

    def _extract_entities(self, blackboard: ConversationBlackboard, patient_message: str) -> None:
        lowered = (patient_message or "").lower()
        if any(token in lowered for token in ["interest undi", "interested", "avunu", "vastanu", "vasthanu", "ostanu", "i will come"]):
            blackboard.interest_confirmed = True
            blackboard.facts_known["interest"] = "confirmed"
            blackboard.facts_confirmed["interest"] = "confirmed"
        if any(token in lowered for token in ["vastanu", "vasthanu", "ostanu", "i will come", "pakka"]):
            if "attend" not in blackboard.patient_commitments:
                blackboard.patient_commitments.append("attend")
            blackboard.facts_confirmed["attendance"] = "confirmed"
        if any(token in lowered for token in ["callback", "call back", "later", "repu", "tomorrow"]):
            blackboard.callback_requested = True
        if any(token in lowered for token in ["appointment", "book", "schedule"]):
            blackboard.appointment_requested = True

    def _context_from_memory(self, memory: Dict[str, Any]) -> Dict[str, str]:
        known = memory.get("known_facts") or {}
        return {
            "hospital_name": known.get("hospital_name") or memory.get("hospital_name") or "Homeo Pills Hospital",
            "campaign_date": known.get("campaign_date") or memory.get("campaign_date") or "July 15",
            "offer": known.get("offer") or memory.get("offer") or "Free check-up mariyu free homeo medicines",
        }

    def _detect_intent(self, patient_message: str) -> str:
        questions = self.questions.extract_questions(patient_message)
        if questions:
            return "ASK_" + "_".join(question.upper() for question in questions)
        lowered = (patient_message or "").lower()
        if any(token in lowered for token in ["interest ledu", "not interested", "vaddu"]):
            return "NOT_INTERESTED"
        if any(token in lowered for token in ["busy", "callback", "later", "repu"]):
            return "CALLBACK"
        if any(token in lowered for token in ["avunu", "yes", "interested", "interest undi"]):
            return "INTERESTED"
        return "UNKNOWN"

    def _summarize_action(self, ai_reply: str) -> str:
        text = (ai_reply or "").strip()
        if not text:
            return ""
        return text[:160]

    def log_debug(self, blackboard: ConversationBlackboard, plan: BlackboardPlan) -> None:
        logger.info(
            "Conversation Blackboard",
            extra={
                "extra_data": {
                    "conversation_id": blackboard.conversation_id,
                    "conversation_state": blackboard.current_state,
                    "current_goal": blackboard.current_goal,
                    "questions_asked": blackboard.questions_asked,
                    "questions_answered": blackboard.questions_answered,
                    "pending_questions": blackboard.questions_pending,
                    "commitments": blackboard.patient_commitments,
                    "conversation_summary": blackboard.conversation_summary,
                    "reflection_output": blackboard.reflection_output,
                    "planner_decision": plan.planner_decision,
                    "planner_route": plan.route,
                }
            },
        )
