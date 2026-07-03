from typing import Any, Dict, List


class ResponseGoalGenerator:
    """Generates response goals; does not generate final user-facing text."""

    def goal_for(self, intent: str, questions_to_answer: List[str], entities: Dict[str, Any] | None = None) -> str:
        entities = entities or {}
        if intent == "WRONG_NUMBER":
            return "Wrong number. Apologize and end immediately."
        if intent == "EMERGENCY":
            return "Emergency. Advise immediate medical attention and end campaign flow."
        if intent == "CONFIRM_ATTENDANCE":
            return "Patient confirmed attendance. Thank them and close politely."
        if intent == "BUSY":
            return "Patient is busy. Offer callback and ask callback time."
        if intent == "CALLBACK":
            return "Patient gave callback preference. Acknowledge and close politely."
        if intent == "NOT_INTERESTED":
            return "Patient is not interested. Thank them without pressure and close."
        if questions_to_answer:
            return "Answer these patient questions first: " + ", ".join(questions_to_answer)
        if intent == "INTERESTED":
            if entities.get("family_member"):
                return "Patient is asking for a family member. Acknowledge and continue gently."
            return "Explain campaign briefly and ask if they can attend."
        return "Listen, acknowledge briefly, and ask one relevant next question."
