from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConversationBlackboard:
    conversation_id: str
    current_goal: str = "Introduce campaign"
    current_state: str = "ACTIVE"
    patient_name: str = ""
    interest_confirmed: bool = False
    campaign_explained: bool = False
    greeting_done: bool = False
    questions_asked: List[str] = field(default_factory=list)
    questions_answered: List[str] = field(default_factory=list)
    questions_pending: List[str] = field(default_factory=list)
    facts_known: Dict[str, Any] = field(default_factory=dict)
    facts_confirmed: Dict[str, Any] = field(default_factory=dict)
    facts_missing: List[str] = field(default_factory=list)
    patient_commitments: List[str] = field(default_factory=list)
    callback_requested: bool = False
    appointment_requested: bool = False
    last_ai_action: str = ""
    last_patient_intent: str = ""
    conversation_summary: str = ""
    reflection_output: str = ""
    planner_decision: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]], conversation_id: str) -> "ConversationBlackboard":
        raw = dict(data or {})
        raw["conversation_id"] = raw.get("conversation_id") or conversation_id
        blackboard = cls(**{key: raw.get(key) for key in cls.__dataclass_fields__ if key in raw})
        blackboard.questions_asked = list(dict.fromkeys(blackboard.questions_asked or []))
        blackboard.questions_answered = list(dict.fromkeys(blackboard.questions_answered or []))
        blackboard.questions_pending = list(dict.fromkeys(blackboard.questions_pending or []))
        blackboard.facts_known = dict(blackboard.facts_known or {})
        blackboard.facts_confirmed = dict(blackboard.facts_confirmed or {})
        blackboard.facts_missing = list(dict.fromkeys(blackboard.facts_missing or []))
        blackboard.patient_commitments = list(dict.fromkeys(blackboard.patient_commitments or []))
        return blackboard

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "current_goal": self.current_goal,
            "current_state": self.current_state,
            "patient_name": self.patient_name,
            "interest_confirmed": self.interest_confirmed,
            "campaign_explained": self.campaign_explained,
            "greeting_done": self.greeting_done,
            "questions_asked": list(self.questions_asked),
            "questions_answered": list(self.questions_answered),
            "questions_pending": list(self.questions_pending),
            "facts_known": dict(self.facts_known),
            "facts_confirmed": dict(self.facts_confirmed),
            "facts_missing": list(self.facts_missing),
            "patient_commitments": list(self.patient_commitments),
            "callback_requested": self.callback_requested,
            "appointment_requested": self.appointment_requested,
            "last_ai_action": self.last_ai_action,
            "last_patient_intent": self.last_patient_intent,
            "conversation_summary": self.conversation_summary,
            "reflection_output": self.reflection_output,
            "planner_decision": self.planner_decision,
        }


@dataclass(frozen=True)
class BlackboardPlan:
    current_goal: str
    planner_decision: str
    response_goals: List[str]
    must_answer_questions: List[str]
    avoid: List[str]
    direct_response: Optional[str] = None
    route: str = "DIALOGUE_FLOW"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_goal": self.current_goal,
            "planner_decision": self.planner_decision,
            "response_goals": list(self.response_goals),
            "must_answer_questions": list(self.must_answer_questions),
            "avoid": list(self.avoid),
            "direct_response": self.direct_response,
            "route": self.route,
        }
