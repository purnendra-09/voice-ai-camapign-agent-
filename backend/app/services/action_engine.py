from typing import Any, Dict, List

from app.conversation_engine.action_repository import get_action_repository
from app.conversation_engine.action_selector import DatasetActionSelector
from app.conversation_engine.response_goal_builder import DatasetResponseGoalBuilder
from app.conversation_engine.state_transition_engine import DatasetStateTransitionEngine
from app.services.action_models import ActionContext, BusinessAction, SUPPORTED_ACTIONS
from app.services.action_rules import ActionRules
from app.services.action_selector import ActionSelector


class BusinessActionEngine:
    """Workflow brain that returns exactly one business action."""

    def __init__(self):
        self.repository = get_action_repository()
        self.dataset_selector = DatasetActionSelector(self.repository)
        self.transition_engine = DatasetStateTransitionEngine(self.repository)
        self.goal_builder = DatasetResponseGoalBuilder()
        self.rules = ActionRules()
        self.selector = ActionSelector()

    def decide(
        self,
        patient_message: str,
        current_state: str,
        patient_intent: str,
        memory: Dict[str, Any],
        hospital_context: Dict[str, Any],
        campaign_context: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
    ) -> BusinessAction:
        context = ActionContext(
            patient_message=patient_message,
            current_state=current_state,
            patient_intent=patient_intent,
            memory=memory,
            hospital_context=hospital_context,
            campaign_context=campaign_context,
            conversation_history=conversation_history,
        )
        dataset_row = self.dataset_selector.select(current_state, patient_intent, memory)
        if dataset_row:
            action = self._from_dataset_row(dataset_row, context)
        else:
            action = self.rules.apply(context) or self.selector.select(context)
        if action.action not in SUPPORTED_ACTIONS:
            raise ValueError(f"Unsupported business action: {action.action}")
        return action

    def _from_dataset_row(self, row, context: ActionContext) -> BusinessAction:
        close = row.next_state == "FINISHED"
        questions_to_answer = self._questions_for_action(row.action)
        questions_to_ask = self._questions_to_ask(row.action, context)
        return BusinessAction(
            action=row.action,
            goal=self.goal_builder.build(row),
            next_state=row.next_state,
            close_conversation=close,
            questions_to_answer=questions_to_answer,
            questions_to_ask=questions_to_ask,
            avoid=[
                "repeat greeting",
                "repeat campaign",
                "ask if interested again",
                "hallucinate",
                "guess hospital information",
            ],
            outcome_hint=self._outcome(row.expected_outcome),
            deterministic_response=self._response_for_action(row.action, context),
            metadata={"dataset_row": row.__dict__},
        )

    def _questions_for_action(self, action: str) -> List[str]:
        mapping = {
            "ANSWER_LOCATION": ["location"],
            "ANSWER_TIME": ["time"],
            "ANSWER_DOCTOR": ["doctor"],
            "ANSWER_CAMPAIGN": ["campaign"],
            "ANSWER_FAQ": ["faq"],
        }
        return mapping.get(action, [])

    def _questions_to_ask(self, action: str, context: ActionContext) -> List[str]:
        if action in {"ANSWER_LOCATION", "ANSWER_TIME", "ANSWER_DOCTOR", "ANSWER_CAMPAIGN"}:
            if context.memory.get("interest_confirmed"):
                return []
            return ["attendance"]
        if action == "ACKNOWLEDGE_INTEREST":
            return ["questions"]
        if action == "OFFER_CALLBACK":
            return ["callback_time"]
        return []

    def _outcome(self, expected_outcome: str) -> str | None:
        mapping = {
            "INTERESTED": "Interested",
            "NOT_INTERESTED": "Not Interested",
            "CALLBACK": "Callback Requested",
            "WRONG_NUMBER": "Wrong Number",
            "EMERGENCY": "Emergency",
            "COMPLETED": "Interested",
        }
        return mapping.get(expected_outcome)

    def _response_for_action(self, action: str, context: ActionContext) -> str | None:
        date = context.campaign_context.get("campaign_date", "July 15")
        hospital = context.hospital_context.get("hospital_name", "Homeo Pills Hospital")
        lowered = context.patient_message.lower()
        if action == "ACKNOWLEDGE_INTEREST" and any(
            token in lowered for token in ["amma", "nanna", "father", "mother", "family", "wife", "husband", "kosam"]
        ):
            return "Sare andi. Mee family member ki ee camp gurinchi cheppagalara? Free check-up mariyu free homeo medicines untayi."
        if action == "ANSWER_CAMPAIGN" and any(
            token in lowered for token in ["hospital nundi", "hospital aa", "meeru hospital", "are you from hospital", "homeo pills nundi"]
        ):
            return f"Avunu andi, {hospital} campaign kosam call chestunnanu. {date} free health camp gurinchi invite cheyyadaniki call chesanu."
        responses = {
            "INTRODUCE_CAMPAIGN": f"Namaskaram andi. Nenu {hospital} nundi maatladutunnanu. {date} free health camp gurinchi oka nimisham cheppacha?",
            "EXPLAIN_CAMPAIGN": f"{date} na free health camp undi andi. Free check-up mariyu free homeo medicines untayi. Meeru attend avvalanukuntunnara?",
            "ACKNOWLEDGE_INTEREST": "Chaala santosham andi. Mee questions emaina unnaya?",
            "HANDLE_NOT_INTERESTED": "Parledandi. Mee samayam ichinanduku dhanyavadalu andi.",
            "ANSWER_LOCATION": f"Camp ekkada jarugutundo naaku ippudu clear details levu andi. Hospital team exact place share chestaru. {date} camp ki ravadaniki meeku interest unda?",
            "ANSWER_TIME": f"Camp time naaku ippudu clear ga available ledu andi. Hospital team correct time confirm chestaru. Meeru {date} ravagalara?",
            "ANSWER_DOCTOR": "Doctor details naaku ippudu clear ga available levu andi. Hospital team akkada guide chestaru.",
            "ANSWER_CAMPAIGN": "Free check-up mariyu free homeo medicines untayi andi. Doctor check chesaka team guide chestaru.",
            "CONFIRM_ATTENDANCE": f"Chaala santosham andi. {date} camp ki tappakunda randi. {hospital} team akkada guide chestaru. Dhanyavadalu.",
            "OFFER_CALLBACK": "Parledandi. Meeku eppudu callback cheyyali?",
            "END_WRONG_NUMBER": "Kshaminchandi andi. Inconvenience ki sorry. Manchi roju.",
            "HANDLE_EMERGENCY": "Idi urgent la undi andi. Dayachesi immediate medical attention teesukondi. Emergency aithe 108 ki call cheyyandi.",
            "CLOSE_CONVERSATION": "Dhanyavadalu andi. Manchi roju.",
        }
        return responses.get(action)
