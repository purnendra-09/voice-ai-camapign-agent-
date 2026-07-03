from fastapi import APIRouter

from app.models import (
    CampaignCallRequest,
    CampaignCallResponse,
    CampaignImportRequest,
    CampaignImportResponse,
    CampaignStatsResponse,
    LeadResponse,
    NextLeadRequest,
    NextLeadResponse,
    TranscriptAnalysisRequest,
    TranscriptAnalysisResponse,
)
from app.services import CampaignOrchestrator, CampaignService


def create_campaigns_router(
    campaign_service: CampaignService,
    orchestrator: CampaignOrchestrator,
) -> APIRouter:
    """Create campaign management and transcript analysis endpoints."""

    router = APIRouter(prefix="/campaigns", tags=["campaigns"])

    @router.post("/import", response_model=CampaignImportResponse)
    async def import_campaign(request: CampaignImportRequest):
        result = campaign_service.import_campaign(request.campaign_id)
        return CampaignImportResponse(**result)

    @router.post("/next-lead", response_model=NextLeadResponse)
    async def next_lead(request: NextLeadRequest):
        lead = campaign_service.get_next_lead(request.campaign_id)
        if not lead:
            return NextLeadResponse(success=False, message="No pending leads available")
        return NextLeadResponse(success=True, lead=LeadResponse(**lead))

    @router.post("/start-call", response_model=CampaignCallResponse)
    async def start_call(request: CampaignCallRequest):
        result = campaign_service.start_call(request.campaign_id, request.row_number)
        return CampaignCallResponse(**result)

    @router.post("/analyze-call", response_model=TranscriptAnalysisResponse)
    async def analyze_call(request: TranscriptAnalysisRequest):
        result = await orchestrator.complete_call(
            campaign_id=request.campaign_id,
            row_number=request.row_number,
            transcript=request.transcript,
            metadata=request.metadata,
        )
        return TranscriptAnalysisResponse(**result)

    @router.get("/{campaign_id}/stats", response_model=CampaignStatsResponse)
    async def campaign_stats(campaign_id: str):
        stats = campaign_service.get_stats(campaign_id)
        return CampaignStatsResponse(campaign_id=campaign_id, **stats)

    @router.post("/{campaign_id}/retry-failed")
    async def retry_failed(campaign_id: str):
        return campaign_service.retry_failed_calls(campaign_id)

    return router
