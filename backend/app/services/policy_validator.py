from app.services.planner_models import PolicyPlan, VALID_INTENTS, VALID_STATES


class PolicyValidator:
    """Validates policy output before it reaches the prompt builder."""

    def validate(self, plan: PolicyPlan) -> PolicyPlan:
        if plan.current_state not in VALID_STATES:
            plan.current_state = "LISTENING"
        if plan.next_state not in VALID_STATES:
            plan.next_state = "LISTENING"
        if plan.patient_intent not in VALID_INTENTS:
            plan.patient_intent = "UNKNOWN"
        if "repeat greeting" in plan.avoid and "greeting" in plan.questions_to_ask:
            plan.questions_to_ask.remove("greeting")
        if "ask if interested again" in plan.avoid:
            plan.questions_to_ask = [q for q in plan.questions_to_ask if q not in {"interest", "attendance"}]
        if len(plan.questions_to_ask) > 1:
            plan.questions_to_ask = plan.questions_to_ask[:1]
        return plan
