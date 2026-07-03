from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


VALID_STATES = {
    "START",
    "GREETING",
    "INTRODUCTION",
    "CAMPAIGN_INTRODUCTION",
    "CAMPAIGN_EXPLANATION",
    "LISTENING",
    "INTEREST_CHECK",
    "INTEREST_CONFIRMED",
    "PATIENT_INTERESTED",
    "PATIENT_NOT_INTERESTED",
    "PATIENT_BUSY",
    "CALLBACK_REQUESTED",
    "CALLBACK",
    "ANSWERING_QUESTION",
    "QUESTION_ANSWERING",
    "COLLECTING_DETAILS",
    "CONFIRMING_ATTENDANCE",
    "CLOSING",
    "FINISHED",
    "WRONG_NUMBER",
    "EMERGENCY",
}

VALID_INTENTS = {
    "GREETING",
    "GOODBYE",
    "INTERESTED",
    "NOT_INTERESTED",
    "ASK_LOCATION",
    "ASK_TIME",
    "ASK_DOCTOR",
    "ASK_MEDICINE",
    "ASK_CAMPAIGN",
    "ASK_FEE",
    "ASK_CONTACT",
    "ASK_IDENTITY",
    "ASK_PURPOSE",
    "ASK_MEMORY",
    "ASK_SUMMARY",
    "ASK_CONVERSATION_SUMMARY",
    "ASK_PREVIOUS_QUESTION",
    "ASK_PREVIOUS_RESPONSE",
    "ASK_PATIENT_COMMITMENT",
    "ASK_AI_IDENTITY",
    "ASK_CONVERSATION_TOPIC",
    "ASK_UNEXPECTED",
    "ASK_REPEAT",
    "ASK_LANGUAGE_CHANGE",
    "CALLBACK",
    "BUSY",
    "WRONG_NUMBER",
    "EMERGENCY",
    "CONFIRM_ATTENDANCE",
    "ALREADY_TREATED",
    "UNKNOWN",
    "CONTINUE",
}


@dataclass
class DialogueMemory:
    patient_name: Optional[str] = None
    language: str = "Telugu"
    greeted: bool = False
    campaign_explained: bool = False
    interest_confirmed: bool = False
    location_shared: bool = False
    time_shared: bool = False
    questions_answered: List[str] = field(default_factory=list)
    questions_pending: List[str] = field(default_factory=list)
    appointment_requested: bool = False
    callback_requested: bool = False
    callback_time: Optional[str] = None
    current_state: str = "START"
    outcome_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_name": self.patient_name,
            "language": self.language,
            "greeted": self.greeted,
            "campaign_explained": self.campaign_explained,
            "interest_confirmed": self.interest_confirmed,
            "location_shared": self.location_shared,
            "time_shared": self.time_shared,
            "questions_answered": list(self.questions_answered),
            "questions_pending": list(self.questions_pending),
            "appointment_requested": self.appointment_requested,
            "callback_requested": self.callback_requested,
            "callback_time": self.callback_time,
            "current_state": self.current_state,
            "outcome_hint": self.outcome_hint,
        }


@dataclass
class PolicyContext:
    patient_message: str
    conversation_history: List[Dict[str, str]]
    memory: DialogueMemory
    hospital_context: Dict[str, Any]
    campaign_details: Dict[str, Any]


@dataclass
class PolicyPlan:
    current_state: str
    patient_intent: str
    emotion: str
    confidence: float
    goal: str
    questions_to_answer: List[str]
    questions_to_ask: List[str]
    avoid: List[str]
    next_state: str
    close_conversation: bool
    requires_tool: bool = False
    tool: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    memory_updates: Dict[str, Any] = field(default_factory=dict)
    required_facts: Dict[str, Any] = field(default_factory=dict)
    forbidden_claims: List[str] = field(default_factory=list)
    deterministic_response: Optional[str] = None
    outcome_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_state": self.current_state,
            "patient_intent": self.patient_intent,
            "emotion": self.emotion,
            "confidence": self.confidence,
            "goal": self.goal,
            "questions_to_answer": self.questions_to_answer,
            "questions_to_ask": self.questions_to_ask,
            "avoid": self.avoid,
            "next_state": self.next_state,
            "close_conversation": self.close_conversation,
            "requires_tool": self.requires_tool,
            "tool": self.tool,
            "entities": self.entities,
            "memory_updates": self.memory_updates,
            "required_facts": self.required_facts,
            "forbidden_claims": self.forbidden_claims,
            "deterministic_response": self.deterministic_response,
            "outcome_hint": self.outcome_hint,
            # Compatibility keys for existing tests/debug panels.
            "state": self.current_state.lower(),
            "intent": self.patient_intent.lower(),
            "response_goal": self.goal,
            "should_end": self.close_conversation,
        }
