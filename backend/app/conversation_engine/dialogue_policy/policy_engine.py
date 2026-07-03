from typing import Any, Dict, List

from app.conversation_engine.dialogue_policy.planner import DialoguePlanner
from app.conversation_engine.dialogue_policy.policy_rules import (
    ACTION_BY_QUESTION,
    GOAL_BY_QUESTION,
    DialoguePolicyRules,
)
from app.conversation_engine.dialogue_policy.question_manager import QuestionManager
from app.conversation_engine.dialogue_policy.response_plan import ResponsePlan
from app.conversation_engine.dialogue_policy.response_validator import DialogueResponseValidator
from app.conversation_engine.conversation_intelligence import AnswerAssembler, MemoryQueryEngine, QuestionDecomposer
from app.services.intent_detector import IntentDetector
from app.services.entity_extractor import EntityExtractor
from app.services.planner_models import PolicyPlan
from app.utils import get_logger


logger = get_logger(__name__)


class DialoguePolicyEngine:
    """Decision maker for every turn. The state machine only records outcomes."""

    def __init__(self):
        self.intent_detector = IntentDetector()
        self.entity_extractor = EntityExtractor()
        self.questions = QuestionManager()
        self.rules = DialoguePolicyRules()
        self.validator = DialogueResponseValidator()
        self.planner = DialoguePlanner()
        self.answer_assembler = AnswerAssembler()
        self.memory_queries = MemoryQueryEngine()
        self.decomposer = QuestionDecomposer()

    def plan(self, session: Dict[str, Any]) -> PolicyPlan:
        history: List[Dict[str, str]] = session.get("messages", [])
        patient_message = self._latest_patient_message(history)
        memory = session.setdefault("dialogue_memory", {})
        current_state = memory.get("current_state", "GREETING")
        base_intent = self.intent_detector.detect(patient_message)
        latest_questions = self.decomposer.decompose_keys(patient_message)
        if not latest_questions:
            latest_questions = self.questions.extract(patient_message)
        detected_intent = self.rules.intent_from_questions(latest_questions, base_intent)
        entities = self.entity_extractor.extract(patient_message)
        question_state = self.questions.update_before_plan(session, latest_questions)
        questions_to_answer = self.rules.select_questions_to_answer(
            detected_intent,
            question_state.get("pending", []),
            latest_questions,
        )
        response_plan = self._build_response_plan(
            session=session,
            patient_message=patient_message,
            current_state=current_state,
            detected_intent=detected_intent,
            entities=entities,
            memory=memory,
            questions_to_answer=questions_to_answer,
            question_state=question_state,
        )
        response_plan = self.validator.validate_plan(response_plan)
        self.questions.mark_answered(session, response_plan.questions_to_answer)
        policy_plan = self.planner.to_policy_plan(response_plan)
        self._apply_memory(session, response_plan)
        logger.info(
            "Dialogue policy decision",
            extra={
                "extra_data": {
                    "conversation_state": current_state,
                    "current_goal": response_plan.goal,
                    "detected_intent": detected_intent,
                    "detected_entities": entities,
                    "pending_questions": response_plan.pending_questions,
                    "answered_questions": response_plan.answered_questions,
                    "policy_decision": response_plan.action,
                    "knowledge_files_loaded": response_plan.knowledge_needed,
                    "planner_output": response_plan.to_dict(),
                    "validation_result": "valid",
                }
            },
        )
        return policy_plan

    def _build_response_plan(
        self,
        session: Dict[str, Any],
        patient_message: str,
        current_state: str,
        detected_intent: str,
        entities: Dict[str, Any],
        memory: Dict[str, Any],
        questions_to_answer: List[str],
        question_state: Dict[str, List[str]],
    ) -> ResponsePlan:
        context = self._context(session)
        avoid = self.rules.avoid_list(memory)
        required_facts = {
            "hospital_name": context["hospital_name"],
            "campaign_date": context["campaign_date"],
            "offer": context["offer"],
        }
        forbidden = ["venue", "exact timings", "doctors", "address", "phone number"]

        if detected_intent == "EMERGENCY":
            return self._fixed_plan(current_state, detected_intent, "Handle emergency", "HANDLE_EMERGENCY", "FINISHED", "DISTRESSED", "Idi urgent la undi andi. Dayachesi immediate medical attention teesukondi. Emergency aithe 108 ki call cheyyandi.", avoid, required_facts, forbidden, close=True, outcome="Emergency")
        if detected_intent == "WRONG_NUMBER":
            return self._fixed_plan(current_state, detected_intent, "Close wrong number", "END_WRONG_NUMBER", "FINISHED", "NEUTRAL", "Kshaminchandi andi. Inconvenience ki sorry. Manchi roju.", avoid, required_facts, forbidden, close=True, outcome="Wrong Number")
        if detected_intent == "NOT_INTERESTED":
            return self._fixed_plan(current_state, detected_intent, "Handle objection", "HANDLE_NOT_INTERESTED", "FINISHED", "NEGATIVE", "Parledandi. Mee samayam ichinanduku dhanyavadalu andi.", avoid, required_facts, forbidden, close=True, outcome="Not Interested")
        if detected_intent == "ALREADY_TREATED":
            return self._fixed_plan(current_state, detected_intent, "Close after prior treatment", "END_CONVERSATION", "FINISHED", "NEUTRAL", "Bagundi andi. Mee arogyam bagundali ani korukuntunnam. Dhanyavadalu.", avoid, required_facts, forbidden, close=True, outcome="Already Treated")
        if detected_intent in {"BUSY", "CALLBACK"}:
            return self._fixed_plan(current_state, detected_intent, "Schedule callback", "OFFER_CALLBACK", "CALLBACK_REQUESTED", "NEUTRAL", "Parledandi. Meeku eppudu callback cheyyali?", avoid, required_facts, forbidden, ask=["callback_time"], outcome="Callback Requested")
        if detected_intent == "CONFIRM_ATTENDANCE":
            response = f"Chaala santosham andi. {context['campaign_date']} camp ki tappakunda randi. {context['hospital_name']} team akkada guide chestaru. Dhanyavadalu."
            return self._fixed_plan(current_state, detected_intent, "Confirm attendance", "CONFIRM_ATTENDANCE", "FINISHED", "POSITIVE", response, avoid, required_facts, forbidden, close=True, outcome="Interested", updates={"interest_confirmed": True})
        if detected_intent == "GOODBYE":
            return self._fixed_plan(current_state, detected_intent, "Close conversation", "CLOSE_CONVERSATION", "FINISHED", "NEUTRAL", "Dhanyavadalu andi. Manchi roju.", avoid, required_facts, forbidden, close=True)

        if "unexpected" in question_state.get("asked", []) and detected_intent == "ASK_UNEXPECTED":
            return ResponsePlan(
                current_state=current_state,
                detected_intent=detected_intent,
                goal="Redirect off-topic question",
                action="REDIRECT_OFF_TOPIC",
                next_state="LISTENING",
                response_goal="Politely decline off-topic topic and redirect to hospital campaign.",
                questions_to_answer=[],
                questions_to_ask=[],
                pending_questions=question_state.get("pending", []),
                answered_questions=question_state.get("answered", []),
                avoid=avoid,
                rules=["never answer weather, politics, cricket, movies, loans, or unrelated topics"],
                deterministic_response="Adi nenu help cheyyalenu andi. Nenu Homeo Pills Hospital free health camp gurinchi matrame help cheyyagalanu.",
                entities=entities,
                required_facts=required_facts,
                forbidden_claims=forbidden,
                confidence=0.95,
            )

        memory_intent = self.memory_queries.detect(patient_message)
        if "memory" in questions_to_answer or memory_intent or detected_intent in {
            "ASK_MEMORY",
            "ASK_SUMMARY",
            "ASK_CONVERSATION_SUMMARY",
            "ASK_PREVIOUS_QUESTION",
            "ASK_PREVIOUS_RESPONSE",
            "ASK_PATIENT_COMMITMENT",
            "ASK_CONVERSATION_TOPIC",
        }:
            summary = self._memory_answer(session, patient_message, memory_intent or detected_intent)
            return ResponsePlan(
                current_state=current_state,
                detected_intent=memory_intent or detected_intent,
                goal="Answer from conversation memory",
                action="ANSWER_MEMORY",
                next_state="LISTENING",
                response_goal="Answer the patient's memory question from tracked conversation state.",
                questions_to_answer=["memory"],
                pending_questions=question_state.get("pending", []),
                answered_questions=question_state.get("answered", []),
                avoid=avoid,
                deterministic_response=f"{summary}.",
                entities=entities,
                required_facts=required_facts,
                forbidden_claims=forbidden,
                confidence=0.94,
            )

        if questions_to_answer:
            return self._question_answer_plan(
                current_state,
                detected_intent,
                entities,
                memory,
                questions_to_answer,
                question_state,
                context,
                avoid,
                required_facts,
                forbidden,
            )

        if detected_intent == "GREETING":
            response = f"{context['campaign_date']} free health camp gurinchi call chesanu andi. Oka nimisham cheppacha?"
            return self._fixed_plan(current_state, detected_intent, "Introduce campaign", "INTRODUCE_CAMPAIGN", "CAMPAIGN_INTRODUCTION", "NEUTRAL", response, avoid, required_facts, forbidden, updates={"campaign_explained": True})
        if detected_intent == "INTERESTED":
            if entities.get("family_member"):
                return self._fixed_plan(
                    current_state,
                    detected_intent,
                    "Handle family interest",
                    "ACKNOWLEDGE_INTEREST",
                    "QUESTION_ANSWERING",
                    "POSITIVE",
                    "Sare andi. Mee family member ki ee camp gurinchi cheppagalara? Free check-up mariyu free homeo medicines untayi.",
                    avoid,
                    required_facts,
                    forbidden,
                    outcome="Interested",
                    updates={"interest_confirmed": True},
                )
            return self._fixed_plan(current_state, detected_intent, "Confirm interest", "ACKNOWLEDGE_INTEREST", "QUESTION_ANSWERING", "POSITIVE", "Chaala santosham andi. Mee questions emaina unnaya?", avoid, required_facts, forbidden, outcome="Interested", updates={"interest_confirmed": True})

        return ResponsePlan(
            current_state=current_state,
            detected_intent=detected_intent,
            goal="Clarify confusion",
            action="CLARIFY_CONFUSION",
            next_state="LISTENING",
            response_goal="Acknowledge confusion and invite a campaign-related question without asking interest again.",
            pending_questions=question_state.get("pending", []),
            answered_questions=question_state.get("answered", []),
            avoid=avoid,
            deterministic_response="Artham ayindi andi. Homeo Pills Hospital free health camp gurinchi emaina doubt unte cheppandi.",
            entities=entities,
            required_facts=required_facts,
            forbidden_claims=forbidden,
            confidence=0.72,
        )

    def _question_answer_plan(self, current_state, detected_intent, entities, memory, questions, question_state, context, avoid, required_facts, forbidden) -> ResponsePlan:
        response = self._answer_questions(questions, context, memory)
        main_question = questions[0]
        return ResponsePlan(
            current_state=current_state,
            detected_intent=detected_intent,
            goal=GOAL_BY_QUESTION.get(main_question, "Answer patient questions"),
            action=ACTION_BY_QUESTION.get(main_question, "ANSWER_QUESTION"),
            next_state="QUESTION_ANSWERING",
            response_goal="Answer pending patient questions before any new question.",
            knowledge_needed=self.rules.knowledge_needed(questions),
            questions_to_answer=questions,
            questions_to_ask=[],
            pending_questions=question_state.get("pending", []),
            answered_questions=question_state.get("answered", []),
            avoid=avoid,
            rules=["answer pending questions first", "do not ask interest while pending questions exist"],
            deterministic_response=response,
            entities=entities,
            memory_updates=self._question_memory_updates(questions),
            required_facts=required_facts,
            forbidden_claims=forbidden,
            confidence=0.95,
        )

    def _answer_questions(self, questions: List[str], context: Dict[str, str], memory: Dict[str, Any]) -> str:
        return self.answer_assembler.assemble(
            questions,
            context=context,
            include_follow_up=len(questions) > 1,
        )

    def _memory_answer(self, session: Dict[str, Any], patient_message: str, detected_intent: str) -> str:
        memory = session.get("dialogue_memory") or {}
        state = session.get("dialogue_questions") or {}
        blackboard_like = type(
            "PolicyMemoryView",
            (),
            {
                "questions_asked": state.get("asked", []),
                "questions_answered": state.get("answered", []),
                "questions_pending": state.get("pending", []),
                "patient_commitments": ["attend"] if memory.get("interest_confirmed") else [],
                "interest_confirmed": bool(memory.get("interest_confirmed")),
                "last_ai_action": self._last_assistant_message(session),
                "patient_name": (session.get("lead") or {}).get("patient_name", ""),
            },
        )()
        return self.memory_queries.answer(
            detected_intent,
            blackboard=blackboard_like,
            memory={
                "previous_ai_reply": self._last_assistant_message(session),
                "previous_commitments": blackboard_like.patient_commitments,
                "patient_name": blackboard_like.patient_name,
                "questions_asked": state.get("asked", []),
                "questions_answered": state.get("answered", []),
                "questions_pending": state.get("pending", []),
            },
            lead=session.get("lead") or {},
        )

    def _last_assistant_message(self, session: Dict[str, Any]) -> str:
        for message in reversed(session.get("messages", [])):
            if message.get("role") == "assistant":
                return message.get("content") or ""
        return ""

    def _fixed_plan(self, current_state, intent, goal, action, next_state, emotion, response, avoid, required_facts, forbidden, ask=None, close=False, outcome=None, updates=None):
        return ResponsePlan(
            current_state=current_state,
            detected_intent=intent,
            goal=goal,
            action=action,
            next_state=next_state,
            response_goal=goal,
            questions_to_ask=ask or [],
            avoid=avoid,
            deterministic_response=response,
            close_conversation=close,
            outcome_hint=outcome,
            memory_updates=updates or {},
            required_facts=required_facts,
            forbidden_claims=forbidden,
            emotion=emotion,
        )

    def _question_memory_updates(self, questions: List[str]) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        if any(question in questions for question in ["campaign", "purpose", "identity"]):
            updates["campaign_explained"] = True
        return updates

    def _apply_memory(self, session: Dict[str, Any], plan: ResponsePlan) -> None:
        memory = session.setdefault("dialogue_memory", {})
        memory["previous_state"] = memory.get("current_state")
        memory["current_state"] = plan.next_state
        memory["last_action"] = plan.action
        memory["last_detected_intent"] = plan.detected_intent
        memory["current_goal"] = plan.goal
        if plan.outcome_hint:
            memory["outcome_hint"] = plan.outcome_hint
        memory.update(plan.memory_updates)

    def _context(self, session: Dict[str, Any]) -> Dict[str, str]:
        lead = session.get("lead") or {}
        raw = lead.get("raw") or {}
        return {
            "hospital_name": raw.get("hospital_name") or "Homeo Pills Hospital",
            "campaign_date": raw.get("campaign_date") or "July 15",
            "offer": raw.get("offer") or "Free check-up and free homeo medicines",
        }

    def _latest_patient_message(self, history: List[Dict[str, str]]) -> str:
        for message in reversed(history):
            if message.get("role") == "user":
                return message.get("content") or ""
        return ""
