from typing import Any, Dict, List


QUESTION_LABELS = {
    "identity": "evaru maatladuthunnaru ani",
    "purpose": "enduku call chesaru ani",
    "campaign": "camp gurinchi",
    "location": "venue ekkada ani",
    "time": "timing gurinchi",
    "doctor": "doctor availability gurinchi",
    "medicine": "medicines gurinchi",
    "fee": "free/cost gurinchi",
    "contact": "contact details gurinchi",
}


class ConversationReflection:
    """Builds natural answers about what has happened in the conversation."""

    def summarize_discussion(self, blackboard: Any, memory: Dict[str, Any] | None = None) -> str:
        memory = memory or {}
        asked = list(dict.fromkeys(getattr(blackboard, "questions_asked", []) or memory.get("questions_asked", []) or []))
        answered = list(dict.fromkeys(getattr(blackboard, "questions_answered", []) or memory.get("questions_answered", []) or []))
        pending = list(dict.fromkeys(getattr(blackboard, "questions_pending", []) or memory.get("questions_pending", []) or []))
        commitments = getattr(blackboard, "patient_commitments", []) or memory.get("previous_commitments") or []
        pieces: List[str] = []
        if asked:
            pieces.append("Meeru " + ", ".join(QUESTION_LABELS.get(q, q) for q in asked) + " adigaru")
        if answered:
            pieces.append("Nenu " + ", ".join(QUESTION_LABELS.get(q, q) for q in answered) + " answer chesanu")
        if pending:
            pieces.append("Inka " + ", ".join(QUESTION_LABELS.get(q, q) for q in pending) + " pending undi")
        if commitments:
            pieces.append("Meeru attend avuthanu ani confirm chesaru")
        return ". ".join(pieces) + ("." if pieces else "Ippati varaku main discussion record lo ledu andi.")
