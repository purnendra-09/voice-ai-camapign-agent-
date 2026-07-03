from app.services.planner_models import VALID_STATES


class ConversationStateMachine:
    """Deterministic state transition policy."""

    def next_state(self, current_state: str, intent: str) -> str:
        transitions = {
            "WRONG_NUMBER": "WRONG_NUMBER",
            "EMERGENCY": "EMERGENCY",
            "ALREADY_TREATED": "CLOSING",
            "CONFIRM_ATTENDANCE": "CLOSING",
            "NOT_INTERESTED": "CLOSING",
            "BUSY": "PATIENT_BUSY",
            "CALLBACK": "CALLBACK_REQUESTED",
            "ASK_LOCATION": "ANSWERING_QUESTION",
            "ASK_TIME": "ANSWERING_QUESTION",
            "ASK_DOCTOR": "ANSWERING_QUESTION",
            "ASK_MEDICINE": "ANSWERING_QUESTION",
            "ASK_CAMPAIGN": "ANSWERING_QUESTION",
            "ASK_FEE": "ANSWERING_QUESTION",
            "ASK_CONTACT": "ANSWERING_QUESTION",
            "ASK_REPEAT": "ANSWERING_QUESTION",
            "INTERESTED": "PATIENT_INTERESTED",
        }
        next_state = transitions.get(intent, "LISTENING")
        return next_state if next_state in VALID_STATES else current_state

    def final_state(self, state: str, close_conversation: bool) -> str:
        if state in {"WRONG_NUMBER", "EMERGENCY"}:
            return "FINISHED"
        if close_conversation:
            return "FINISHED"
        return state
