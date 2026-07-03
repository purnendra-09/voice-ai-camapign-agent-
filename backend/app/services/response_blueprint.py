from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ResponseBlueprint:
    """What should be said. The LLM may only decide natural wording."""

    acknowledge: bool = True
    thank_patient: bool = False
    repeat_campaign: bool = False
    repeat_interest: bool = False
    repeat_greeting: bool = False
    answer_questions: List[str] = field(default_factory=list)
    ask_question: Optional[str] = None
    tone: str = "warm"
    length: str = "short"
    emotion: str = "friendly"
    conversation_goal: str = ""
    must_include: List[str] = field(default_factory=list)
    must_not_include: List[str] = field(default_factory=list)
    max_sentences: int = 3
    deterministic_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "acknowledge": self.acknowledge,
            "thank_patient": self.thank_patient,
            "repeat_campaign": self.repeat_campaign,
            "repeat_interest": self.repeat_interest,
            "repeat_greeting": self.repeat_greeting,
            "answer_questions": self.answer_questions,
            "ask_question": self.ask_question,
            "tone": self.tone,
            "length": self.length,
            "emotion": self.emotion,
            "conversation_goal": self.conversation_goal,
            "must_include": self.must_include,
            "must_not_include": self.must_not_include,
            "max_sentences": self.max_sentences,
            "deterministic_text": self.deterministic_text,
        }
