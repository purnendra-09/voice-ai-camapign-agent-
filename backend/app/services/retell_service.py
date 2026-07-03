from typing import Any, Dict

from app.services.campaign_orchestrator import CampaignOrchestrator


class RetellService:
    """Handles Retell AI webhook events for campaign calls."""

    def __init__(self, orchestrator: CampaignOrchestrator):
        self.orchestrator = orchestrator

    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process a Retell webhook payload."""
        event = payload.get("event") or payload.get("event_type") or "unknown"
        metadata = payload.get("metadata") or {}
        campaign_id = payload.get("campaign_id") or metadata.get("campaign_id")
        row_number = payload.get("row_number") or metadata.get("row_number")
        transcript = payload.get("transcript") or payload.get("transcript_text")

        if event not in {"call_analyzed", "call_ended", "transcript_ready"}:
            return {
                "success": True,
                "event": event,
                "processed": False,
                "message": "Webhook acknowledged; no analysis required for this event",
            }

        if not campaign_id or not row_number or not transcript:
            return {
                "success": False,
                "event": event,
                "processed": False,
                "message": "Missing campaign_id, row_number, or transcript",
            }

        result = await self.orchestrator.complete_call(
            campaign_id=str(campaign_id),
            row_number=int(row_number),
            transcript=str(transcript),
            metadata=metadata,
        )
        return {
            "success": result.get("success", False),
            "event": event,
            "processed": True,
            "message": "Transcript analyzed and campaign updated",
            "analysis": result.get("outcome"),
        }
