from typing import Any, Dict, List


QUESTION_LABELS = {
    "identity": "caller identity",
    "purpose": "call purpose",
    "campaign": "camp details",
    "location": "venue",
    "time": "timing",
    "doctor": "doctor availability",
    "medicine": "medicines",
    "fee": "fee",
    "contact": "contact details",
    "memory": "conversation memory",
}


class ConversationSummarizer:
    """Maintains a compact live summary from blackboard state."""

    def summarize(self, blackboard: Any, memory: Dict[str, Any] | None = None) -> str:
        memory = memory or {}
        parts: List[str] = []
        if getattr(blackboard, "greeting_done", False):
            parts.append("Greeting completed")
        if getattr(blackboard, "campaign_explained", False):
            parts.append("Campaign explained")
        if getattr(blackboard, "interest_confirmed", False):
            parts.append("Patient interested")
        commitments = getattr(blackboard, "patient_commitments", []) or memory.get("previous_commitments") or []
        if commitments:
            parts.append("Attendance confirmed")
        answered = getattr(blackboard, "questions_answered", []) or []
        pending = getattr(blackboard, "questions_pending", []) or []
        for question in answered:
            parts.append(f"{QUESTION_LABELS.get(question, question).title()} answered")
        for question in pending:
            parts.append(f"{QUESTION_LABELS.get(question, question).title()} pending")
        return ". ".join(dict.fromkeys(parts)) + ("." if parts else "")
