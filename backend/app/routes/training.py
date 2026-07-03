from fastapi import APIRouter

from app.models import (
    TrainingFinishRequest,
    TrainingMessageRequest,
    TrainingMessageResponse,
    TrainingReportResponse,
    TrainingStartRequest,
    TrainingStartResponse,
)
from app.services import LocalTrainingService


def create_training_router(training_service: LocalTrainingService) -> APIRouter:
    """Create local AI campaign training endpoints."""

    router = APIRouter(prefix="/training", tags=["local-training"])

    @router.post("/sessions", response_model=TrainingStartResponse)
    async def start_session(request: TrainingStartRequest):
        result = await training_service.start_session(
            campaign_id=request.campaign_id,
            row_number=request.row_number,
            client_id=request.client_id,
            prompt_key=request.prompt_key or "campaign_calling",
        )
        return TrainingStartResponse(**result)

    @router.post("/sessions/{session_id}/messages", response_model=TrainingMessageResponse)
    async def send_message(session_id: str, request: TrainingMessageRequest):
        result = await training_service.send_message(session_id, request.message)
        return TrainingMessageResponse(**result)

    @router.post("/sessions/{session_id}/finish", response_model=TrainingReportResponse)
    async def finish_session(session_id: str, request: TrainingFinishRequest):
        result = await training_service.finish_session(
            session_id=session_id,
            notes=request.notes,
            update_excel=request.update_excel,
        )
        return TrainingReportResponse(**result)

    @router.get("/sessions/{session_id}", response_model=TrainingReportResponse)
    async def session_report(session_id: str):
        result = training_service.report(session_id)
        return TrainingReportResponse(**result)

    return router
