from app.services.phrase_library import TeluguPhraseLibrary
from app.services.planner_models import PolicyPlan
from app.services.response_blueprint import ResponseBlueprint


class ResponsePlanner:
    """Turns policy decisions into response blueprints."""

    def __init__(self):
        self.phrases = TeluguPhraseLibrary()

    def build_blueprint(self, plan: PolicyPlan) -> ResponseBlueprint:
        ask_question = self._question_from_plan(plan)
        return ResponseBlueprint(
            acknowledge=True,
            thank_patient=plan.close_conversation,
            repeat_campaign=False,
            repeat_interest=False,
            repeat_greeting=False,
            answer_questions=plan.questions_to_answer,
            ask_question=ask_question,
            tone="warm",
            length="short",
            emotion=plan.emotion.lower(),
            conversation_goal=plan.goal,
            must_include=self._must_include(plan),
            must_not_include=plan.avoid + plan.forbidden_claims,
            max_sentences=3,
            deterministic_text=plan.deterministic_response,
        )

    def _question_from_plan(self, plan: PolicyPlan) -> str | None:
        if not plan.questions_to_ask:
            return None
        question = plan.questions_to_ask[0]
        if question == "attendance":
            return "July 15 camp ki ravadaniki meeku interest unda?"
        if question == "interest":
            return "Camp gurinchi interest unda andi?"
        if question == "callback_time":
            return "Meeku eppudu callback cheyyali?"
        return question

    def _must_include(self, plan: PolicyPlan) -> list[str]:
        facts = plan.required_facts
        includes: list[str] = []
        if plan.patient_intent in {"ASK_LOCATION", "ASK_TIME"}:
            includes.append("details are not clear now")
        if plan.patient_intent in {"ASK_FEE", "ASK_MEDICINE", "INTERESTED", "CONFIRM_ATTENDANCE"}:
            includes.append(str(facts.get("campaign_date", "July 15")))
        return includes
