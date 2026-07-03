from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ResponsePlan:
    """Provider-neutral decision for the next assistant reply."""

    current_state: str
    detected_intent: str
    goal: str
    action: str
    next_state: str
    response_goal: str
    knowledge_needed: List[str] = field(default_factory=list)
    questions_to_answer: List[str] = field(default_factory=list)
    questions_to_ask: List[str] = field(default_factory=list)
    pending_questions: List[str] = field(default_factory=list)
    answered_questions: List[str] = field(default_factory=list)
    skipped_questions: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    avoid: List[str] = field(default_factory=list)
    tool_needed: Optional[str] = None
    expected_tone: str = "warm"
    deterministic_response: Optional[str] = None
    close_conversation: bool = False
    outcome_hint: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    memory_updates: Dict[str, Any] = field(default_factory=dict)
    required_facts: Dict[str, Any] = field(default_factory=dict)
    forbidden_claims: List[str] = field(default_factory=list)
    confidence: float = 0.9
    emotion: str = "NEUTRAL"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_state": self.current_state,
            "detected_intent": self.detected_intent,
            "goal": self.goal,
            "action": self.action,
            "next_state": self.next_state,
            "response_goal": self.response_goal,
            "knowledge_needed": list(self.knowledge_needed),
            "questions_to_answer": list(self.questions_to_answer),
            "questions_to_ask": list(self.questions_to_ask),
            "pending_questions": list(self.pending_questions),
            "answered_questions": list(self.answered_questions),
            "skipped_questions": list(self.skipped_questions),
            "rules": list(self.rules),
            "avoid": list(self.avoid),
            "tool_needed": self.tool_needed,
            "expected_tone": self.expected_tone,
            "deterministic_response": self.deterministic_response,
            "close_conversation": self.close_conversation,
            "outcome_hint": self.outcome_hint,
            "entities": dict(self.entities),
            "memory_updates": dict(self.memory_updates),
            "required_facts": dict(self.required_facts),
            "forbidden_claims": list(self.forbidden_claims),
            "confidence": self.confidence,
            "emotion": self.emotion,
        }
