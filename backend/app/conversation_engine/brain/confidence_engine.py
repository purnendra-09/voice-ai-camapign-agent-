from typing import Any, Dict


class ConfidenceEngine:
    """Estimates whether the planned answer can be stated confidently."""

    def score(self, plan: Dict[str, Any], understanding: Dict[str, Any]) -> Dict[str, Any]:
        confidence = 92
        reasons = []
        missing = set(understanding.get("missing_information") or [])
        questions = set(plan.get("questions_to_answer") or [])
        risky = {"location", "time", "doctor", "contact"}
        if questions.intersection(risky):
            confidence -= 18
            reasons.append("requested fact may be unconfirmed")
        if plan.get("patient_intent") == "UNKNOWN":
            confidence -= 20
            reasons.append("intent confidence is low")
        if missing:
            reasons.append("business rules forbid guessing missing facts")
        level = "High" if confidence >= 85 else "Medium" if confidence >= 70 else "Low"
        return {"score": max(confidence, 0), "level": level, "reasons": reasons}
