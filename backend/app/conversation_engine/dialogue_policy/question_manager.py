import re
from typing import Any, Dict, Iterable, List


QUESTION_RULES = {
    "identity": [r"who are you", r"who is calling", r"evaru", r"meeru evaru", r"hospital nundi", r"hospital aa"],
    "purpose": [r"why.*call", r"enduku.*call", r"enduku andi", r"purpose", r"what is this call"],
    "campaign": [r"camp enti", r"health camp", r"event enti", r"campaign", r"em chestaru", r"details"],
    "location": [r"venue", r"address", r"ekkada", r"location", r"place", r"ravali"],
    "time": [r"time", r"timing", r"eppudu", r"morning", r"evening", r"slot"],
    "doctor": [r"doctor", r"\bdr\b", r"specialist", r"eye doctor"],
    "medicine": [r"medicine", r"medicines", r"mandulu", r"tablet", r"pills", r"tests"],
    "fee": [r"free", r"fee", r"cost", r"charge", r"dabbu", r"payment"],
    "memory": [r"what did i ask", r"em adiganu", r"naa peru", r"did i say", r"attend avuthanu", r"what happened", r"summary"],
    "unexpected": [r"weather", r"politics", r"cricket", r"movie", r"loan"],
}


class QuestionManager:
    """Extracts and tracks patient questions without relying on the model."""

    def extract(self, message: str) -> List[str]:
        text = (message or "").lower()
        found: List[str] = []
        for question, patterns in QUESTION_RULES.items():
            if any(re.search(pattern, text) for pattern in patterns):
                found.append(question)
        return found

    def update_before_plan(self, session: Dict[str, Any], questions: Iterable[str]) -> Dict[str, List[str]]:
        state = session.setdefault(
            "dialogue_questions",
            {"asked": [], "answered": [], "pending": [], "skipped": []},
        )
        asked = list(dict.fromkeys(state.get("asked", [])))
        answered = list(dict.fromkeys(state.get("answered", [])))
        pending = list(dict.fromkeys(state.get("pending", [])))
        skipped = list(dict.fromkeys(state.get("skipped", [])))
        for question in questions:
            if question not in asked:
                asked.append(question)
            if question not in answered and question not in pending and question != "unexpected":
                pending.append(question)
        state.update({"asked": asked, "answered": answered, "pending": pending, "skipped": skipped})
        return state

    def mark_answered(self, session: Dict[str, Any], questions: Iterable[str]) -> Dict[str, List[str]]:
        state = session.setdefault(
            "dialogue_questions",
            {"asked": [], "answered": [], "pending": [], "skipped": []},
        )
        answered = list(dict.fromkeys(state.get("answered", [])))
        resolved = set(questions or [])
        for question in questions:
            if question not in answered:
                answered.append(question)
        pending = [question for question in state.get("pending", []) if question not in resolved]
        state.update({"answered": answered, "pending": pending})
        return state

    def summary_text(self, session: Dict[str, Any]) -> str:
        state = session.get("dialogue_questions") or {}
        asked = state.get("asked") or []
        answered = state.get("answered") or []
        pending = state.get("pending") or []
        parts = []
        if asked:
            parts.append("Meeru " + ", ".join(asked) + " gurinchi adigaru")
        if answered:
            parts.append("Nenu " + ", ".join(answered) + " answer chesanu")
        if pending:
            parts.append("Inka " + ", ".join(pending) + " pending undi")
        return ". ".join(parts) if parts else "Ippati varaku main questions record lo levu andi"

    def memory_answer(self, session: Dict[str, Any], patient_message: str) -> str:
        text = (patient_message or "").lower()
        lead = session.get("lead") or {}
        memory = session.get("dialogue_memory") or {}
        if "naa peru" in text:
            return f"Mee peru {lead.get('patient_name') or 'Ravi Kumar'} andi"
        if "attend avuthanu" in text or "did i say" in text:
            if memory.get("interest_confirmed"):
                return "Avunu andi, meeru attend avuthanu ani chepparu"
            return "Ippati varaku meeru attend confirm cheyyaledu andi"
        return self.summary_text(session)
