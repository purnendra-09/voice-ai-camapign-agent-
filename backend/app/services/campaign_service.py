from typing import Any, Dict, Optional

from app.services.excel_service import ExcelService
from app.utils import get_logger

logger = get_logger(__name__)


class CampaignService:
    """Coordinates campaign progress and lead selection."""

    def __init__(self, excel_service: ExcelService):
        self.excel = excel_service

    def import_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Inspect a campaign sheet and return import readiness details."""
        validation = self.excel.validate_columns()
        if not validation.get("valid"):
            return {
                "success": False,
                "campaign_id": campaign_id,
                "error": validation.get("message"),
                "missing": validation.get("missing", []),
            }

        stats = self.excel.campaign_stats(campaign_id)
        pending = len(self.excel.find_pending_leads(campaign_id))
        return {
            "success": True,
            "campaign_id": campaign_id,
            "total_leads": stats["total"],
            "pending_leads": pending,
        }

    def get_next_lead(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Return the next pending lead for a campaign."""
        pending = self.excel.find_pending_leads(campaign_id)
        return pending[0] if pending else None

    def start_call(self, campaign_id: str, row_number: Optional[int] = None) -> Dict[str, Any]:
        """Mark a lead as calling and return the lead selected."""
        lead = self.excel.get_lead_by_row(row_number) if row_number else self.get_next_lead(campaign_id)
        if not lead:
            return {
                "success": False,
                "campaign_id": campaign_id,
                "status": "no_pending_leads",
                "message": "No pending leads available",
            }

        updated = self.excel.mark_call_started(lead["row_number"])
        return {
            "success": updated,
            "campaign_id": campaign_id,
            "row_number": lead["row_number"],
            "status": "calling" if updated else "failed",
            "message": "Call marked as started" if updated else "Failed to update lead",
            "lead": lead,
        }

    def get_stats(self, campaign_id: str) -> Dict[str, Any]:
        """Return campaign statistics."""
        return self.excel.campaign_stats(campaign_id)

    def retry_failed_calls(self, campaign_id: str) -> Dict[str, Any]:
        """Mark failed no-answer/busy calls as retry candidates."""
        retryable = {"busy", "no answer", "failed"}
        updated = 0
        for lead in self.excel.read_leads():
            if not self.excel._matches_campaign(lead, campaign_id):
                continue
            outcome = (lead.get("outcome") or lead.get("status") or "").lower()
            if outcome in retryable and self.excel.update_lead(lead["row_number"], {"status": "retry"}):
                updated += 1
        return {"campaign_id": campaign_id, "retry_marked": updated}
