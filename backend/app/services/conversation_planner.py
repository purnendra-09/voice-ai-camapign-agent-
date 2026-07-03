from app.services.dialogue_policy_engine import DialoguePolicyEngine
from app.services.planner_models import PolicyPlan


PlannerOutput = PolicyPlan


class ConversationPlanner:
    """Compatibility wrapper around the Dialogue Policy Engine."""

    def __init__(self):
        self.engine = DialoguePolicyEngine()

    def plan(self, session):
        return self.engine.plan(session)


class PlannerPromptBuilder:
    """Converts policy JSON into a compact provider-neutral LLM prompt."""

    def build(self, plan: PolicyPlan, transcript: str) -> str:
        return (
            "The Dialogue Policy Engine has already decided the next step. "
            "You must follow this JSON plan exactly. You only choose natural wording.\n"
            f"POLICY_PLAN_JSON: {plan.to_dict()}\n\n"
            "Rules: answer questions_to_answer first; ask only questions_to_ask; "
            "do not repeat anything listed in avoid; never mention forbidden_claims; "
            "do not invent missing facts; no markdown; keep it short in natural Telugu.\n\n"
            f"Conversation so far:\n{transcript}\n\n"
            "Return only the next assistant reply."
        )


class ResponseValidator:
    """Guards final LLM wording against the policy plan."""

    def validate(self, text: str, plan: PolicyPlan) -> str:
        clean = (text or "").strip()
        if not clean:
            return self.fallback(plan)
        lowered = clean.lower()
        forbidden_terms = ["amalapuram", "9 am", "10 am", "doctor available", "phone number is"]
        if any(term in lowered for term in forbidden_terms):
            return self.fallback(plan)
        if any(claim in lowered for claim in [item.lower() for item in plan.forbidden_claims if item not in {"venue"}]):
            return self.fallback(plan)
        if len(clean.split()) > 55:
            return self.fallback(plan)
        if clean.count("?") > 1:
            return self.fallback(plan)
        return clean

    def fallback(self, plan: PolicyPlan) -> str:
        if plan.deterministic_response:
            return plan.deterministic_response
        if plan.questions_to_ask:
            question = plan.questions_to_ask[0]
            if question in {"attendance", "interest"}:
                return "Artham ayindi andi. July 15 free health camp ki ravadaniki interest unda?"
            if question == "callback_time":
                return "Parledandi. Meeku eppudu callback cheyyali?"
        return "Artham ayindi andi. July 15 free health camp gurinchi inka emaina doubt unda?"
