from typing import List

from app.conversation_engine.dialogue_policy.response_plan import ResponsePlan


class DialogueResponseValidator:
    """Validates policy output before it becomes a spoken response."""

    def validate_plan(self, plan: ResponsePlan) -> ResponsePlan:
        if plan.questions_to_answer:
            plan.questions_to_ask = []
            if "answer pending questions before asking anything new" not in plan.rules:
                plan.rules.append("answer pending questions before asking anything new")
        if "ask if interested again" in plan.avoid:
            plan.questions_to_ask = [q for q in plan.questions_to_ask if q not in {"interest", "attendance"}]
        plan.questions_to_ask = plan.questions_to_ask[:1]
        return plan

    def validate_text(self, text: str, plan: ResponsePlan) -> List[str]:
        lowered = (text or "").lower()
        violations: List[str] = []
        if plan.questions_to_answer and "?" in text:
            violations.append("asked a new question before answering pending questions")
        if "repeat greeting" in plan.avoid and any(token in lowered for token in ["namaskaram", "hello"]):
            violations.append("repeated greeting")
        if "ask if interested again" in plan.avoid and "interest" in lowered:
            violations.append("asked interest again")
        if any(term in lowered for term in ["amalapuram", "9 am", "10 am", "confirmed appointment"]):
            violations.append("hallucinated restricted fact")
        return violations
