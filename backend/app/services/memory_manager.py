from typing import Any, Dict

from app.services.planner_models import DialogueMemory, PolicyPlan


class MemoryManager:
    """Maintains structured dialogue memory on the session object."""

    def from_session(self, session: Dict[str, Any]) -> DialogueMemory:
        lead = session.get("lead") or {}
        stored = session.setdefault("dialogue_memory", {})
        return DialogueMemory(
            patient_name=lead.get("patient_name"),
            language=lead.get("language") or stored.get("language", "Telugu"),
            greeted=bool(stored.get("greeted", True)),
            campaign_explained=bool(stored.get("campaign_explained", False)),
            interest_confirmed=bool(stored.get("interest_confirmed", False)),
            location_shared=bool(stored.get("location_shared", False)),
            time_shared=bool(stored.get("time_shared", False)),
            questions_answered=list(stored.get("questions_answered", [])),
            questions_pending=list(stored.get("questions_pending", [])),
            appointment_requested=bool(stored.get("appointment_requested", False)),
            callback_requested=bool(stored.get("callback_requested", False)),
            callback_time=stored.get("callback_time"),
            current_state=stored.get("current_state", "GREETING"),
            outcome_hint=stored.get("outcome_hint"),
        )

    def apply_plan(self, session: Dict[str, Any], plan: PolicyPlan) -> None:
        memory = session.setdefault("dialogue_memory", {})
        memory["previous_state"] = memory.get("current_state")
        memory.update(plan.memory_updates)
        memory["current_state"] = plan.next_state
        memory["last_action"] = plan.entities.get("business_action")
        if plan.outcome_hint:
            memory["outcome_hint"] = plan.outcome_hint
        answered = set(memory.get("questions_answered", []))
        answered.update(plan.questions_to_answer)
        memory["questions_answered"] = sorted(answered)
        pending = [q for q in memory.get("questions_pending", []) if q not in answered]
        for question in plan.questions_to_ask:
            if question not in pending and question not in answered:
                pending.append(question)
        memory["questions_pending"] = pending
