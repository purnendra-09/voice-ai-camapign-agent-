from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from app.conversation_engine.dataset_loader import ActionDatasetRow, ConversationActionDatasetLoader


class ActionRepository:
    """Single source of truth for conversation actions and transitions."""

    def __init__(self, rows: List[ActionDatasetRow]):
        self.rows = rows

    def find_by_state(self, state: str) -> List[ActionDatasetRow]:
        state = state.upper()
        return [row for row in self.rows if row.state == state]

    def find_by_intent(self, intent: str) -> List[ActionDatasetRow]:
        intent = intent.upper()
        return [row for row in self.rows if row.intent == intent]

    def find_transition(self, state: str, intent: str) -> Optional[ActionDatasetRow]:
        state = state.upper()
        intent = intent.upper()
        exact = next((row for row in self.rows if row.state == state and row.intent == intent), None)
        if exact:
            return exact
        any_state = next((row for row in self.rows if row.state == "ANY" and row.intent == intent), None)
        if any_state:
            return any_state
        return next((row for row in self.rows if row.intent == intent), None)

    def find_expected_action(self, state: str, intent: str) -> Optional[str]:
        row = self.find_transition(state, intent)
        return row.action if row else None


@lru_cache(maxsize=1)
def get_action_repository(dataset_path: str | None = None) -> ActionRepository:
    loader = ConversationActionDatasetLoader(Path(dataset_path) if dataset_path else None)
    return ActionRepository(loader.load())

