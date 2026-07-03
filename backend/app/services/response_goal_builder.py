from app.services.action_models import BusinessAction


class ResponseGoalBuilder:
    """Builds concise goals for the language layer from business actions."""

    def build(self, action: BusinessAction) -> str:
        base = action.goal.strip()
        if action.questions_to_answer:
            base += " Answer: " + ", ".join(action.questions_to_answer) + "."
        if action.questions_to_ask:
            base += " Ask only: " + action.questions_to_ask[0] + "."
        base += " Keep response under three short sentences."
        return base
