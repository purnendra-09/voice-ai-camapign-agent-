from typing import Any, Dict

from app.models import CallOutcome


class OutcomeService:
    """Normalizes and validates campaign call outcomes."""

    ALLOWED_OUTCOMES = {
        "Interested",
        "Not Interested",
        "Busy",
        "No Answer",
        "Wrong Number",
        "Callback Requested",
        "Already Treated",
        "Appointment Requested",
        "Emergency",
        "Other",
    }

    def normalize(self, outcome: Dict[str, Any]) -> CallOutcome:
        """Return a safe CallOutcome with a known status."""
        status = str(outcome.get("status") or "Other").strip()
        if status.lower() in {item.lower() for item in self.ALLOWED_OUTCOMES}:
            status = next(item for item in self.ALLOWED_OUTCOMES if item.lower() == status.lower())
        else:
            status = "Other"

        return CallOutcome(
            status=status,
            summary=str(outcome.get("summary") or "Call completed."),
            next_action=str(outcome.get("next_action") or self._default_next_action(status)),
            follow_up_required=bool(outcome.get("follow_up_required", status in {"Interested", "Callback Requested", "Appointment Requested", "Emergency"})),
            confidence=float(outcome.get("confidence") or 0.0),
            sentiment=outcome.get("sentiment"),
            intent=outcome.get("intent"),
            notes=outcome.get("notes"),
        )

    def _default_next_action(self, status: str) -> str:
        defaults = {
            "Interested": "Sales or care team should follow up.",
            "Not Interested": "Do not call again for this campaign.",
            "Busy": "Retry later.",
            "No Answer": "Retry later.",
            "Wrong Number": "Verify phone number.",
            "Callback Requested": "Schedule callback.",
            "Already Treated": "Close lead or move to future nurture campaign.",
            "Appointment Requested": "Route to appointment team.",
            "Emergency": "Escalate immediately to hospital staff.",
        }
        return defaults.get(status, "Review manually.")
