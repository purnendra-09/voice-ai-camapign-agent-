from typing import Any, Dict

from app.services.campaign_service import CampaignService
from app.services.conversation_analyzer import ConversationAnalyzer
from app.services.excel_service import ExcelService
from app.utils import get_logger

logger = get_logger(__name__)


class CampaignOrchestrator:
    """Coordinates campaign calls from lead selection through Excel update."""

    def __init__(
        self,
        campaign_service: CampaignService,
        excel_service: ExcelService,
        analyzer: ConversationAnalyzer,
    ):
        self.campaigns = campaign_service
        self.excel = excel_service
        self.analyzer = analyzer

    async def complete_call(
        self,
        campaign_id: str,
        row_number: int,
        transcript: str,
        metadata: Dict[str, Any] | None = None,
        update_excel: bool = True,
    ) -> Dict[str, Any]:
        """Analyze a completed call and persist the structured outcome."""
        lead = self.excel.get_lead_by_row(row_number)
        context = {
            "campaign_id": campaign_id,
            "lead": lead or {},
            "metadata": metadata or {},
        }
        outcome = await self.analyzer.analyze_transcript(transcript, context)
        updated = self.excel.update_outcome(row_number, outcome.model_dump()) if update_excel else False
        logger.info(
            "Campaign call completed",
            extra={
                "extra_data": {
                    "campaign_id": campaign_id,
                    "row_number": row_number,
                    "outcome": outcome.status,
                    "updated": updated,
                    "update_excel": update_excel,
                }
            },
        )
        return {
            "success": updated,
            "campaign_id": campaign_id,
            "row_number": row_number,
            "outcome": outcome,
            "updated": updated,
        }
