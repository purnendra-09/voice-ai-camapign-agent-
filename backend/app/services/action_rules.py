from typing import Optional

from app.services.action_models import ActionContext, BusinessAction
from app.services.response_goal_builder import ResponseGoalBuilder


class ActionRules:
    """Business rules that override ordinary action selection."""

    def __init__(self):
        self.goal_builder = ResponseGoalBuilder()

    def apply(self, context: ActionContext) -> Optional[BusinessAction]:
        if context.patient_intent == "WRONG_NUMBER":
            return self._action(
                "HANDLE_WRONG_NUMBER",
                "Wrong number. Apologize and end immediately.",
                "FINISHED",
                close=True,
                outcome="Wrong Number",
                response="Kshaminchandi andi. Inconvenience ki sorry. Manchi roju.",
            )
        if context.patient_intent == "EMERGENCY":
            return self._action(
                "HANDLE_EMERGENCY",
                "Emergency. Advise immediate medical attention and end campaign flow.",
                "FINISHED",
                close=True,
                outcome="Emergency",
                response="Idi urgent la undi andi. Dayachesi immediate medical attention teesukondi. Emergency aithe 108 ki call cheyyandi.",
            )
        if context.patient_intent == "NOT_INTERESTED":
            return self._action(
                "HANDLE_NOT_INTERESTED",
                "Respect the patient's decision. Thank them politely. End conversation.",
                "FINISHED",
                close=True,
                outcome="Not Interested",
                response="Parledandi. Mee samayam ichinanduku dhanyavadalu andi.",
            )
        if context.patient_intent == "BUSY":
            return self._action(
                "HANDLE_BUSY",
                "Patient is busy. Offer callback and ask callback time.",
                "CALLBACK_REQUESTED",
                ask=["callback_time"],
                outcome="Callback Requested",
                response="Parledandi. Meeku eppudu callback cheyyali?",
            )
        if context.patient_intent == "CALLBACK":
            return self._action(
                "HANDLE_CALLBACK",
                "Acknowledge callback preference and close politely.",
                "FINISHED",
                close=True,
                outcome="Callback Requested",
                response="Sare andi. Aa time lo callback cheyyadaniki note chestanu. Dhanyavadalu.",
            )
        if context.patient_intent == "CONFIRM_ATTENDANCE":
            date = context.campaign_context.get("campaign_date", "July 15")
            hospital = context.hospital_context.get("hospital_name", "Homeo Pills Hospital")
            return self._action(
                "CONFIRM_ATTENDANCE",
                "Patient confirmed attendance. Thank the patient and move toward closing.",
                "FINISHED",
                close=True,
                outcome="Interested",
                response=f"Chala santosham andi. {date} camp ki tappakunda randi. {hospital} team meeku akkada guide chestaru. Dhanyavadalu.",
            )
        return None

    def _action(
        self,
        action: str,
        goal: str,
        next_state: str,
        close: bool = False,
        answer: list[str] | None = None,
        ask: list[str] | None = None,
        outcome: str | None = None,
        response: str | None = None,
    ) -> BusinessAction:
        business_action = BusinessAction(
            action=action,
            goal=goal,
            next_state=next_state,
            close_conversation=close,
            questions_to_answer=answer or [],
            questions_to_ask=ask or [],
            avoid=["repeat greeting", "repeat campaign", "ask if interested again", "hallucinate"],
            outcome_hint=outcome,
            deterministic_response=response,
        )
        business_action.goal = self.goal_builder.build(business_action)
        return business_action
