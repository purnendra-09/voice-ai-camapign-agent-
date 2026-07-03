import re
from typing import Any, Dict, Optional

from app.conversation_engine.conversation_intelligence.conversation_reflection import ConversationReflection


class MemoryQueryEngine:
    """Answers conversation-aware questions from tracked memory instead of the LLM."""

    PATTERNS = {
        "ASK_PREVIOUS_QUESTION": [r"what did i ask", r"nenu em adiganu", r"em adiganu", r"what have i asked"],
        "ASK_PREVIOUS_RESPONSE": [r"what did you tell", r"meeru em chepparu", r"nuvvu em cheppavu"],
        "ASK_PATIENT_COMMITMENT": [r"did i say yes", r"did i confirm", r"vastanu ani", r"vasthanu ani", r"attend avuthanu", r"i will come"],
        "ASK_AI_IDENTITY": [r"who are you", r"evaru", r"meeru evaru", r"who is calling"],
        "ASK_CONVERSATION_TOPIC": [r"what are we discussing", r"topic enti", r"em discuss", r"deni gurinchi"],
        "ASK_CONVERSATION_SUMMARY": [r"conversation enti", r"mana conversation", r"summar", r"what happened", r"recap"],
        "ASK_PATIENT_NAME": [r"my name", r"naa peru", r"did i tell.*name"],
    }

    def __init__(self):
        self.reflection = ConversationReflection()

    def detect(self, message: str) -> Optional[str]:
        text = (message or "").lower()
        for intent, patterns in self.PATTERNS.items():
            if any(re.search(pattern, text) for pattern in patterns):
                return intent
        return None

    def answer(self, intent: str, blackboard: Any = None, memory: Dict[str, Any] | None = None, lead: Dict[str, Any] | None = None) -> str:
        memory = memory or {}
        lead = lead or {}
        if intent == "ASK_PREVIOUS_QUESTION":
            asked = self._get_list(blackboard, memory, "questions_asked")
            return "Meeru ippativaraka " + ", ".join(asked) + " gurinchi adigaru." if asked else "Ippati varaku meeru main question adagaledu andi."
        if intent == "ASK_PREVIOUS_RESPONSE":
            previous = memory.get("previous_ai_reply") or getattr(blackboard, "last_ai_action", "")
            return f"Nenu cheppindi: {previous}" if previous else "Ippati varaku nenu main answer cheppaledu andi."
        if intent == "ASK_PATIENT_COMMITMENT":
            commitments = getattr(blackboard, "patient_commitments", []) if blackboard else memory.get("previous_commitments", [])
            interest = bool(getattr(blackboard, "interest_confirmed", False) if blackboard else memory.get("interest_confirmed"))
            return "Avunu andi, meeru attend avuthanu ani chepparu." if commitments or interest else "Ippati varaku meeru attend confirm cheyyaledu andi."
        if intent == "ASK_AI_IDENTITY":
            return "Nenu Homeo Pills Hospital campaign executive la maatladutunnanu andi."
        if intent == "ASK_CONVERSATION_TOPIC":
            return "Mana conversation Homeo Pills Hospital free health camp gurinchi jarugutondi andi."
        if intent == "ASK_PATIENT_NAME":
            name = getattr(blackboard, "patient_name", "") if blackboard else ""
            name = name or memory.get("patient_name") or lead.get("patient_name")
            return f"Mee peru {name} andi." if name else "Mee peru ippati varaku confirm ga record lo ledu andi."
        if intent == "ASK_CONVERSATION_SUMMARY":
            return self.reflection.summarize_discussion(blackboard, memory)
        return self.reflection.summarize_discussion(blackboard, memory)

    def _get_list(self, blackboard: Any, memory: Dict[str, Any], key: str) -> list[str]:
        value = getattr(blackboard, key, None) if blackboard else None
        return list(dict.fromkeys(value or memory.get(key) or []))
