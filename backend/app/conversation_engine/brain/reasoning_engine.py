from typing import Any, Dict, List


class ReasoningEngine:
    """Creates compact internal reasoning from policy output and session state."""

    def understand(self, session: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        messages = session.get("messages", [])
        latest = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        question_state = session.get("dialogue_questions") or {}
        memory = session.get("dialogue_memory") or {}
        return {
            "patient_said": latest,
            "detected_intent": plan.get("patient_intent"),
            "patient_is_asking": list(plan.get("questions_to_answer") or []),
            "already_known": self._known_information(session, memory),
            "missing_information": list(plan.get("forbidden_claims") or []),
            "pending_questions": list(question_state.get("pending") or []),
            "answered_questions": list(question_state.get("answered") or []),
        }

    def reason(self, understanding: Dict[str, Any], plan: Dict[str, Any]) -> List[str]:
        reasoning = []
        intent = understanding.get("detected_intent")
        if understanding.get("patient_is_asking"):
            reasoning.append("Patient asked a direct question, so answer it before any new qualification.")
        if intent in {"ASK_IDENTITY", "ASK_PURPOSE", "ASK_MEMORY"}:
            reasoning.append("Patient needs context or memory, so keep the reply short and do not restart the call.")
        if plan.get("close_conversation"):
            reasoning.append("Policy selected a closing action, so avoid reopening the conversation.")
        if plan.get("forbidden_claims"):
            reasoning.append("Some requested facts are not confirmed, so avoid guessing.")
        if not reasoning:
            reasoning.append("Continue the current campaign flow gently without repetition.")
        return reasoning

    def _known_information(self, session: Dict[str, Any], memory: Dict[str, Any]) -> Dict[str, Any]:
        lead = session.get("lead") or {}
        raw = lead.get("raw") or {}
        return {
            "patient_name": lead.get("patient_name"),
            "hospital_name": raw.get("hospital_name") or "Homeo Pills Hospital",
            "campaign_date": raw.get("campaign_date") or "July 15",
            "interest_confirmed": bool(memory.get("interest_confirmed")),
            "current_state": memory.get("current_state"),
        }
