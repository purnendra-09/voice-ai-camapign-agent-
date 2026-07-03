from typing import Any, Dict


class ConversationStrategy:
    """Tracks conversation progress and next strategic objective."""

    STAGES = {
        "GREETING": 10,
        "CAMPAIGN_INTRODUCTION": 25,
        "LISTENING": 35,
        "QUESTION_ANSWERING": 55,
        "CALLBACK_REQUESTED": 70,
        "CLOSING": 90,
        "FINISHED": 100,
    }

    def build(self, session: Dict[str, Any], policy_plan: Dict[str, Any]) -> Dict[str, Any]:
        memory = session.get("dialogue_memory") or {}
        next_state = policy_plan.get("next_state") or memory.get("current_state") or "LISTENING"
        progress = self.STAGES.get(next_state, 50)
        if memory.get("interest_confirmed"):
            progress = max(progress, 70)
        if policy_plan.get("close_conversation"):
            progress = 100
        return {
            "current_goal": policy_plan.get("goal"),
            "next_goal": self._next_goal(policy_plan, memory),
            "conversation_progress": next_state,
            "completion_percent": progress,
        }

    def _next_goal(self, policy_plan: Dict[str, Any], memory: Dict[str, Any]) -> str:
        if policy_plan.get("close_conversation"):
            return "Keep conversation closed"
        if policy_plan.get("questions_to_answer"):
            return "Check if patient has any remaining campaign questions"
        if not memory.get("interest_confirmed"):
            return "Confirm attendance only after patient questions are answered"
        return "Close politely or support appointment/callback"
