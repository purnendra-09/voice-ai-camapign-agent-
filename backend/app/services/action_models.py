from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SUPPORTED_ACTIONS = {
    "GREET",
    "INTRODUCE_CAMPAIGN",
    "EXPLAIN_CAMPAIGN",
    "ANSWER_LOCATION",
    "ANSWER_TIME",
    "ANSWER_DOCTOR",
    "ANSWER_CAMPAIGN",
    "ANSWER_FAQ",
    "ACKNOWLEDGE_INTEREST",
    "HANDLE_NOT_INTERESTED",
    "HANDLE_BUSY",
    "OFFER_CALLBACK",
    "HANDLE_CALLBACK",
    "HANDLE_WRONG_NUMBER",
    "END_WRONG_NUMBER",
    "HANDLE_EMERGENCY",
    "COLLECT_PATIENT_DETAILS",
    "CONFIRM_ATTENDANCE",
    "ANSWER_UNKNOWN",
    "CLOSE_CONVERSATION",
    "END_CONVERSATION",
    "TRANSFER_TO_HUMAN",
}


@dataclass
class ActionContext:
    patient_message: str
    current_state: str
    patient_intent: str
    memory: Dict[str, Any]
    hospital_context: Dict[str, Any]
    campaign_context: Dict[str, Any]
    conversation_history: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class BusinessAction:
    action: str
    goal: str
    next_state: str
    close_conversation: bool = False
    questions_to_answer: List[str] = field(default_factory=list)
    questions_to_ask: List[str] = field(default_factory=list)
    avoid: List[str] = field(default_factory=list)
    outcome_hint: Optional[str] = None
    deterministic_response: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "goal": self.goal,
            "next_state": self.next_state,
            "close_conversation": self.close_conversation,
            "questions_to_answer": self.questions_to_answer,
            "questions_to_ask": self.questions_to_ask,
            "avoid": self.avoid,
            "outcome_hint": self.outcome_hint,
            "deterministic_response": self.deterministic_response,
            "metadata": self.metadata,
        }
