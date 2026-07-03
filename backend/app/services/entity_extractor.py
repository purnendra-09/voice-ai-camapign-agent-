from typing import Any, Dict


class EntityExtractor:
    """Extracts simple call-control entities without LLM dependency."""

    def extract(self, message: str) -> Dict[str, Any]:
        text = message.lower()
        entities: Dict[str, Any] = {}
        if "repu" in text or "tomorrow" in text:
            entities["callback_day"] = "tomorrow"
        if "morning" in text:
            entities["callback_time"] = "morning"
        if "evening" in text:
            entities["callback_time"] = "evening"
        if "amma" in text or "mother" in text:
            entities["family_member"] = "mother"
        if "nanna" in text or "father" in text:
            entities["family_member"] = "father"
        if any(token in text for token in ["family", "wife", "husband", "kosam"]):
            entities.setdefault("family_member", "family")
        if any(token in text for token in ["hospital nundi", "hospital aa", "meeru hospital", "are you from hospital", "homeo pills nundi"]):
            entities["trust_check"] = True
        return entities
