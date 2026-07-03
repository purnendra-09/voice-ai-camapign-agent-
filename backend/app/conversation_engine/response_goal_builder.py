from app.conversation_engine.dataset_loader import ActionDatasetRow


class DatasetResponseGoalBuilder:
    """Builds response goals from dataset rows."""

    def build(self, row: ActionDatasetRow) -> str:
        goal = row.response_goal.strip()
        if "under three" not in goal.lower():
            goal += " Keep response under three short sentences."
        return goal

