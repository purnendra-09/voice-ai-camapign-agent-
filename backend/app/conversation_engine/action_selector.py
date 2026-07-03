from typing import Dict, Optional

from app.conversation_engine.action_repository import ActionRepository
from app.conversation_engine.dataset_loader import ActionDatasetRow


class DatasetActionSelector:
    """Selects expected action from current state and detected intent."""

    def __init__(self, repository: ActionRepository):
        self.repository = repository

    def select(self, current_state: str, intent: str, memory: Dict[str, object]) -> Optional[ActionDatasetRow]:
        normalized_state = self._normalize_state(current_state, memory)
        return self.repository.find_transition(normalized_state, intent)

    def _normalize_state(self, current_state: str, memory: Dict[str, object]) -> str:
        state = (current_state or "GREETING").upper()
        if state in {"START", "GREETING"}:
            if memory.get("campaign_explained"):
                return "INTEREST_CHECK"
            return "GREETING"
        if state in {"PATIENT_INTERESTED", "INTEREST_CONFIRMED", "ANSWERING_QUESTION", "LISTENING"}:
            return "QUESTION_ANSWERING"
        if state in {"PATIENT_BUSY", "CALLBACK_REQUESTED"}:
            return "CALLBACK"
        return state
