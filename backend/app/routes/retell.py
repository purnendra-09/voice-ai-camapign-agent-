from fastapi import APIRouter

from app.models import RetellWebhookRequest, RetellWebhookResponse
from app.services import RetellService


def create_retell_router(retell_service: RetellService) -> APIRouter:
    """Create Retell AI webhook endpoints."""

    router = APIRouter(prefix="/retell", tags=["retell"])

    @router.post("/webhook", response_model=RetellWebhookResponse)
    async def retell_webhook(request: RetellWebhookRequest):
        payload = request.model_dump()
        payload.update(request.payload)
        result = await retell_service.handle_webhook(payload)
        return RetellWebhookResponse(**result)

    return router
