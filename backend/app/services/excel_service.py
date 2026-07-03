from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.sheets_service import SheetsService
from app.utils import get_logger

logger = get_logger(__name__)


class ExcelService:
    """Campaign spreadsheet adapter built on the existing Google Sheets service."""

    DEFAULT_COLUMN_MAP = {
        "patient_id": "patient_id",
        "patient_name": "patient_name",
        "phone_number": "phone_number",
        "language": "language",
        "campaign": "campaign",
        "priority": "priority",
        "status": "status",
        "call_attempts": "call_attempts",
        "last_call_time": "last_call_time",
        "next_call_time": "next_call_time",
        "outcome": "outcome",
        "summary": "summary",
        "next_action": "next_action",
        "assigned_agent": "assigned_agent",
        "notes": "notes",
    }

    REQUIRED_FIELDS = ["patient_name", "phone_number", "status"]

    def __init__(
        self,
        sheets_service: SheetsService,
        sheet_title: str = "Campaign",
        column_map: Optional[Dict[str, str]] = None,
    ):
        self.sheets = sheets_service
        self.sheet_title = sheet_title
        self.column_map = {**self.DEFAULT_COLUMN_MAP, **(column_map or {})}

    def read_leads(self, sheet_title: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read campaign leads and attach spreadsheet row numbers."""
        title = sheet_title or self.sheet_title
        records = self.sheets.read_all_records(title)
        leads = []
        for index, record in enumerate(records, start=2):
            normalized = self._normalize_record(record)
            normalized["row_number"] = index
            normalized["raw"] = record
            leads.append(normalized)
        return leads

    def validate_columns(self, sheet_title: Optional[str] = None) -> Dict[str, Any]:
        """Validate that required campaign columns are available."""
        title = sheet_title or self.sheet_title
        worksheet = self.sheets.get_sheet(title)
        if not worksheet:
            return {
                "valid": False,
                "missing": self.REQUIRED_FIELDS,
                "message": "Campaign sheet is unavailable",
            }

        headers = {
            self.sheets._normalize_header(header)
            for header in worksheet.row_values(1)
        }
        missing = [
            field
            for field in self.REQUIRED_FIELDS
            if self.sheets._normalize_header(self.column_map.get(field, field)) not in headers
        ]
        return {
            "valid": not missing,
            "missing": missing,
            "message": "OK" if not missing else "Missing required campaign columns",
        }

    def find_pending_leads(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Return leads that belong to a campaign and are ready to call."""
        return [
            lead
            for lead in self.read_leads()
            if self._matches_campaign(lead, campaign_id)
            and lead.get("status", "").strip().lower() in {"", "pending", "retry"}
        ]

    def get_lead_by_row(self, row_number: int) -> Optional[Dict[str, Any]]:
        """Find a lead by spreadsheet row number."""
        for lead in self.read_leads():
            if lead.get("row_number") == row_number:
                return lead
        return None

    def update_lead(self, row_number: int, updates: Dict[str, Any]) -> bool:
        """Update a lead row using backend field names."""
        try:
            worksheet = self.sheets.get_sheet(self.sheet_title)
            if not worksheet:
                return False

            headers = [
                self.sheets._normalize_header(header)
                for header in worksheet.row_values(1)
            ]
            cells = []
            for field, value in updates.items():
                column_name = self.column_map.get(field, field)
                normalized_column = self.sheets._normalize_header(column_name)
                if normalized_column not in headers:
                    logger.warning(f"Skipping update for missing column: {field}")
                    continue
                column_index = headers.index(normalized_column) + 1
                cells.append({
                    "range": self._cell_address(row_number, column_index),
                    "values": [[str(value) if value is not None else ""]],
                })

            if not cells:
                return False

            worksheet.batch_update(cells)
            logger.info(
                "Campaign lead updated",
                extra={"extra_data": {"row_number": row_number, "fields": list(updates.keys())}},
            )
            return True
        except Exception as e:
            logger.error(f"Error updating campaign lead row {row_number}: {str(e)}")
            return False

    def mark_call_started(self, row_number: int) -> bool:
        """Mark a lead as currently being called."""
        lead = self.get_lead_by_row(row_number) or {}
        attempts = self._to_int(lead.get("call_attempts")) + 1
        return self.update_lead(
            row_number,
            {
                "status": "calling",
                "call_attempts": attempts,
                "last_call_time": datetime.utcnow().isoformat(),
            },
        )

    def update_outcome(self, row_number: int, outcome: Dict[str, Any]) -> bool:
        """Persist a structured call outcome to the campaign sheet."""
        return self.update_lead(
            row_number,
            {
                "status": self._status_from_outcome(outcome.get("status")),
                "last_call_time": datetime.utcnow().isoformat(),
                "outcome": outcome.get("status"),
                "summary": outcome.get("summary"),
                "next_action": outcome.get("next_action"),
                "notes": outcome.get("notes") or f"confidence={outcome.get('confidence')}",
            },
        )

    def campaign_stats(self, campaign_id: str) -> Dict[str, Any]:
        """Build campaign status and outcome counts."""
        leads = [
            lead for lead in self.read_leads()
            if self._matches_campaign(lead, campaign_id)
        ]
        by_status: Dict[str, int] = {}
        by_outcome: Dict[str, int] = {}
        for lead in leads:
            status = lead.get("status") or "unknown"
            outcome = lead.get("outcome") or "none"
            by_status[status] = by_status.get(status, 0) + 1
            by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
        return {
            "total": len(leads),
            "by_status": by_status,
            "by_outcome": by_outcome,
        }

    def _normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {}
        for field, column_name in self.column_map.items():
            normalized[field] = record.get(self.sheets._normalize_header(column_name), "")
        return normalized

    def _matches_campaign(self, lead: Dict[str, Any], campaign_id: str) -> bool:
        campaign = lead.get("campaign", "")
        return not campaign or campaign.strip().lower() == campaign_id.strip().lower()

    def _status_from_outcome(self, outcome: Any) -> str:
        normalized = str(outcome or "").strip().lower()
        if normalized in {"callback requested", "busy", "no answer"}:
            return "Callback" if normalized == "callback requested" else "Retry"
        if normalized == "wrong number":
            return "Invalid"
        return "Completed"

    def _to_int(self, value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _cell_address(self, row_number: int, column_index: int) -> str:
        letters = ""
        index = column_index
        while index:
            index, remainder = divmod(index - 1, 26)
            letters = chr(65 + remainder) + letters
        return f"{letters}{row_number}"
