import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


VALID_DATASET_STATES = {
    "ANY",
    "START",
    "GREETING",
    "CAMPAIGN_INTRODUCTION",
    "INTEREST_CHECK",
    "INTEREST_CONFIRMED",
    "QUESTION_ANSWERING",
    "DETAIL_COLLECTION",
    "CONFIRMATION",
    "CALLBACK",
    "CLOSING",
    "FINISHED",
}

REQUIRED_FIELDS = {
    "state",
    "patient_input",
    "intent",
    "action",
    "next_state",
    "response_goal",
    "expected_outcome",
}


@dataclass(frozen=True)
class ActionDatasetRow:
    state: str
    patient_input: str
    intent: str
    action: str
    next_state: str
    response_goal: str
    expected_outcome: str

    @classmethod
    def from_dict(cls, item: Dict[str, Any]) -> "ActionDatasetRow":
        missing = REQUIRED_FIELDS - set(item)
        if missing:
            raise ValueError(f"Dataset row missing fields: {sorted(missing)}")
        return cls(
            state=str(item["state"]).strip().upper(),
            patient_input=str(item["patient_input"]).strip(),
            intent=str(item["intent"]).strip().upper(),
            action=str(item["action"]).strip().upper(),
            next_state=str(item["next_state"]).strip().upper(),
            response_goal=str(item["response_goal"]).strip(),
            expected_outcome=str(item["expected_outcome"]).strip().upper(),
        )


class ConversationActionDatasetLoader:
    """Loads and validates the action dataset during backend startup."""

    def __init__(self, dataset_path: Path | None = None):
        self.dataset_path = dataset_path or self._default_dataset_path()

    def load(self) -> List[ActionDatasetRow]:
        with self.dataset_path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        if not isinstance(raw, list):
            raise ValueError("Conversation action dataset must be a list")
        rows = [ActionDatasetRow.from_dict(item) for item in raw]
        self.validate(rows)
        return rows

    def validate(self, rows: List[ActionDatasetRow]) -> None:
        if not rows:
            raise ValueError("Conversation action dataset is empty")
        seen_transitions: set[tuple[str, str]] = set()
        seen_actions: set[str] = set()
        for row in rows:
            if row.state not in VALID_DATASET_STATES:
                raise ValueError(f"Invalid dataset state: {row.state}")
            if row.next_state not in VALID_DATASET_STATES:
                raise ValueError(f"Invalid dataset next_state: {row.next_state}")
            key = (row.state, row.intent)
            if key in seen_transitions:
                raise ValueError(f"Duplicate state+intent transition: {key}")
            seen_transitions.add(key)
            if not row.action:
                raise ValueError("Dataset action cannot be empty")
            seen_actions.add(row.action)
        if not seen_actions:
            raise ValueError("Dataset must define at least one action")

    def _default_dataset_path(self) -> Path:
        local = Path(__file__).with_name("Conversation_Action_Dataset.json")
        if local.exists():
            return local
        downloads = Path.home() / "Downloads" / "Conversation_Action_Dataset.json"
        if downloads.exists():
            return downloads
        raise FileNotFoundError("Conversation_Action_Dataset.json not found")

