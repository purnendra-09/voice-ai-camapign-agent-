from typing import Any, Dict


class CognitivePlanner:
    """Builds the response goal used by the language layer."""

    def plan(
        self,
        policy_plan: Dict[str, Any],
        understanding: Dict[str, Any],
        emotion: Dict[str, str],
        confidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "response_goal": policy_plan.get("goal"),
            "information_needed": understanding.get("missing_information", []),
            "knowledge_files": (policy_plan.get("entities") or {}).get("response_plan", {}).get("knowledge_needed", []),
            "tone": emotion.get("tone"),
            "length": "one or two short sentences",
            "follow_up": (policy_plan.get("questions_to_ask") or [None])[0],
            "confidence": confidence,
        }
