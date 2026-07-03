from app.services.action_models import ActionContext, BusinessAction
from app.services.response_goal_builder import ResponseGoalBuilder


class ActionSelector:
    """Selects exactly one business action after hard rules."""

    def __init__(self):
        self.goal_builder = ResponseGoalBuilder()

    def select(self, context: ActionContext) -> BusinessAction:
        action = self._select(context)
        action.goal = self.goal_builder.build(action)
        return action

    def _select(self, context: ActionContext) -> BusinessAction:
        intent = context.patient_intent
        date = context.campaign_context.get("campaign_date", "July 15")
        avoid = ["repeat greeting", "hallucinate", "guess hospital information"]
        if context.memory.get("interest_confirmed"):
            avoid.append("ask if interested again")
        if context.memory.get("campaign_explained"):
            avoid.append("repeat campaign")

        if intent == "ASK_LOCATION":
            return BusinessAction(
                action="ANSWER_LOCATION",
                goal="Answer only the venue question. Do not repeat campaign. Do not ask interest again.",
                next_state="ANSWERING_QUESTION",
                questions_to_answer=["location"],
                questions_to_ask=[] if context.memory.get("interest_confirmed") else ["attendance"],
                avoid=avoid,
                deterministic_response=f"Camp ekkada jarugutundo naaku ippudu clear details levu andi. Hospital team exact place share chestaru. {date} camp ki ravadaniki meeku interest unda?",
            )
        if intent == "ASK_TIME":
            return BusinessAction(
                action="ANSWER_TIME",
                goal="Answer only the timing question. Do not guess exact time.",
                next_state="ANSWERING_QUESTION",
                questions_to_answer=["time"],
                questions_to_ask=[] if context.memory.get("interest_confirmed") else ["attendance"],
                avoid=avoid,
                deterministic_response=f"Camp time naaku ippudu clear ga available ledu andi. Hospital team correct time confirm chestaru. Meeru {date} ravagalara?",
            )
        if intent == "ASK_CAMPAIGN":
            if context.memory.get("campaign_explained"):
                goal = "Answer campaign clarification briefly without repeating the full campaign."
            else:
                goal = "Explain campaign briefly."
            hospital = context.hospital_context.get("hospital_name", "Homeo Pills Hospital")
            return BusinessAction(
                action="ANSWER_CAMPAIGN",
                goal=goal,
                next_state="ANSWERING_QUESTION",
                questions_to_answer=["campaign"],
                questions_to_ask=[],
                avoid=avoid,
                deterministic_response=f"Avunu andi, {hospital} campaign kosam call chestunnanu. {date} free health camp gurinchi invite cheyyadaniki call chesanu.",
            )
        if intent in {"ASK_MEDICINE", "ASK_FEE", "ASK_DOCTOR", "ASK_CONTACT", "ASK_REPEAT"}:
            return BusinessAction(
                action="ANSWER_FAQ",
                goal="Answer the patient's FAQ first using only known information.",
                next_state="ANSWERING_QUESTION",
                questions_to_answer=[intent.replace("ASK_", "").lower()],
                questions_to_ask=[] if context.memory.get("interest_confirmed") else ["attendance"],
                avoid=avoid,
            )
        if intent == "INTERESTED":
            if any(key in context.patient_message.lower() for key in ["amma", "nanna", "father", "mother", "family", "wife", "husband", "kosam"]):
                return BusinessAction(
                    action="ACKNOWLEDGE_INTEREST",
                    goal="Patient is asking for a family member. Acknowledge and continue gently.",
                    next_state="INTEREST_CONFIRMED",
                    questions_to_ask=[],
                    avoid=avoid,
                    outcome_hint="Interested",
                    deterministic_response="Sare andi. Mee family member ki ee camp gurinchi cheppagalara? Free check-up mariyu free homeo medicines untayi.",
                )
            return BusinessAction(
                action="ACKNOWLEDGE_INTEREST",
                goal="Thank the patient and ask if they have any questions.",
                next_state="INTEREST_CONFIRMED",
                questions_to_ask=["questions"],
                avoid=avoid,
                outcome_hint="Interested",
            )
        if intent == "ALREADY_TREATED":
            return BusinessAction(
                action="END_CONVERSATION",
                goal="Acknowledge prior treatment and close politely.",
                next_state="FINISHED",
                close_conversation=True,
                avoid=avoid,
                outcome_hint="Already Treated",
                deterministic_response="Bagundi andi. Mee arogyam bagundali ani korukuntunnam. Dhanyavadalu.",
            )
        return BusinessAction(
            action="ANSWER_UNKNOWN",
            goal="Acknowledge briefly and ask one relevant next question.",
            next_state="LISTENING",
            questions_to_ask=[] if context.memory.get("interest_confirmed") else ["interest"],
            avoid=avoid,
        )
