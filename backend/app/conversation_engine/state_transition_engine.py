from app.conversation_engine.action_repository import ActionRepository


class DatasetStateTransitionEngine:
    """State transitions are read only from the dataset."""

    def __init__(self, repository: ActionRepository):
        self.repository = repository

    def next_state(self, current_state: str, intent: str) -> str:
        row = self.repository.find_transition(current_state, intent)
        return row.next_state if row else current_state

