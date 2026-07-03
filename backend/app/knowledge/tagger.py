from pathlib import Path
from typing import List


class KnowledgeTagger:
    """Assign deterministic retrieval tags from filenames and content."""

    FILE_TAGS = {
        "identity": ["identity", "introduction", "caller", "who", "call"],
        "hospital": ["hospital", "location", "doctor", "services", "contact"],
        "campaign": ["campaign", "health camp", "benefits", "date", "venue", "time"],
        "conversation_style": ["style", "tone", "natural", "conversation"],
        "telugu_style": ["telugu", "phrases", "language", "andhra"],
        "business_rules": ["rules", "safety", "repeat", "interest", "hallucination"],
        "faq": ["faq", "question", "answer", "venue", "time", "why", "who"],
        "objection_handling": ["busy", "callback", "not interested", "wrong number", "objection"],
        "response_guidelines": ["response", "quality", "guidelines", "repeat"],
        "conversation_examples": ["examples", "good", "bad", "question", "answer"],
    }

    CONTENT_TAGS = {
        "interest": ["interest"],
        "venue": ["venue", "location"],
        "timing": ["time", "timing"],
        "doctor": ["doctor", "services"],
        "callback": ["callback", "busy"],
        "wrong number": ["wrong number"],
        "not interested": ["not interested"],
        "emergency": ["emergency", "safety"],
    }

    def tags_for(self, path: Path, content: str) -> List[str]:
        stem = path.stem.lower()
        tags = list(self.FILE_TAGS.get(stem, []))
        lowered = content.lower()
        for marker, marker_tags in self.CONTENT_TAGS.items():
            if marker in lowered:
                tags.extend(marker_tags)
        return list(dict.fromkeys(tags))
