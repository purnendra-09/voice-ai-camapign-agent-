from typing import Any, Dict, List, Optional

from .index import KnowledgeIndex
from .models import KnowledgeDocument


class KnowledgeRetriever:
    """Select a compact set of relevant knowledge documents per turn."""

    ALWAYS_INCLUDE = ["identity.md"]

    ROUTES = [
        (["evaru", "who", "call", "ches", "chestunnaru"], ["identity.md", "hospital.md", "conversation_style.md"]),
        (["camp", "venue", "ekkada", "location", "time", "timing", "eppudu"], ["campaign.md", "faq.md", "business_rules.md"]),
        (["interest ledu", "not interested", "vaddu", "busy", "callback", "wrong number"], ["objection_handling.md", "conversation_style.md", "business_rules.md"]),
        (["doctor", "service", "medicine", "consultation"], ["hospital.md", "faq.md", "campaign.md"]),
    ]

    def __init__(self, index: KnowledgeIndex):
        self.index = index

    def retrieve(
        self,
        patient_message: str,
        memory: Dict[str, Any],
        state: Optional[str] = None,
        intent: Optional[str] = None,
        goal: Optional[str] = None,
        limit: int = 6,
    ) -> List[KnowledgeDocument]:
        lowered = (patient_message or "").lower()
        selected = []
        for filename in self.ALWAYS_INCLUDE:
            self._append(selected, filename)

        for markers, files in self.ROUTES:
            if any(marker in lowered for marker in markers):
                for filename in files:
                    self._append(selected, filename)

        tags = self._tags_from_turn(lowered, memory, state, intent, goal)
        query = " ".join([patient_message or "", state or "", intent or "", goal or ""])
        for document in self.index.search(query=query, tags=tags, limit=limit):
            if document not in selected:
                selected.append(document)

        for filename in ["conversation_style.md", "business_rules.md"]:
            if len(selected) < limit:
                self._append(selected, filename)

        return selected[:limit]

    def _append(self, selected: List[KnowledgeDocument], filename: str) -> None:
        document = self.index.get(filename)
        if document and document not in selected:
            selected.append(document)

    def _tags_from_turn(
        self,
        lowered: str,
        memory: Dict[str, Any],
        state: Optional[str],
        intent: Optional[str],
        goal: Optional[str],
    ) -> List[str]:
        text = " ".join([lowered, str(state or ""), str(intent or ""), str(goal or "")]).lower()
        tags = []
        if any(word in text for word in ["who", "evaru", "caller"]):
            tags.extend(["identity", "caller"])
        if any(word in text for word in ["camp", "health", "benefit"]):
            tags.extend(["campaign", "health camp", "benefits"])
        if any(word in text for word in ["venue", "location", "ekkada"]):
            tags.extend(["venue", "location", "faq"])
        if any(word in text for word in ["time", "timing", "eppudu"]):
            tags.extend(["time", "timing", "faq"])
        if any(word in text for word in ["busy", "callback", "interest ledu", "wrong"]):
            tags.extend(["busy", "callback", "not interested", "wrong number"])
        if memory.get("questions_pending"):
            tags.append("faq")
        return list(dict.fromkeys(tags))
