from fastapi import APIRouter, HTTPException, status
from app.models import (
    ConversationRequest,
    ConversationResponse,
    ConversationHistoryRequest,
    ConversationHistoryResponse,
    ClientInfoRequest,
    ClientMetadataResponse,
    ConversationMessage,
)
from app.services import ConversationOrchestrator, ClientManager
from app.utils import get_logger

logger = get_logger(__name__)


def create_conversation_router(
    orchestrator: ConversationOrchestrator,
    client_manager: ClientManager,
) -> APIRouter:
    """Create conversation router with AI and multi-client endpoints"""

    router = APIRouter(prefix="/conversation", tags=["conversation"])

    @router.post("/chat", response_model=ConversationResponse)
    async def chat(request: ConversationRequest):
        """
        Process a conversation message with AI

        Handles:
        - Multi-turn conversations
        - Tool calling for appointments and doctor checks
        - Multi-client support

        Args:
            request: ConversationRequest with message and client_id

        Returns:
            ConversationResponse with AI response
        """
        logger.info(f"Chat request from client: {request.client_id}")

        result = await orchestrator.process_conversation(
            user_input=request.message,
            client_id=request.client_id,
            conversation_id=request.conversation_id,
        )

        if not result.get("success"):
            return ConversationResponse(
                success=False,
                conversation_id=request.conversation_id or "",
                client_id=request.client_id,
                error=result.get("error"),
            )

        return ConversationResponse(
            success=True,
            response=result.get("response"),
            conversation_id=result.get("conversation_id"),
            client_id=result.get("client_id"),
            tools_used=result.get("tools_used"),
            tool_calls_executed=result.get("tool_calls_executed"),
        )

    @router.get("/history")
    async def get_history(conversation_id: str):
        """
        Get conversation history

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation messages
        """
        logger.info(f"Fetching history for conversation: {conversation_id}")

        messages = orchestrator.get_conversation_history(conversation_id)

        if messages is None:
            return ConversationHistoryResponse(
                success=False,
                conversation_id=conversation_id,
                error="Conversation not found",
            )

        return ConversationHistoryResponse(
            success=True,
            conversation_id=conversation_id,
            messages=[ConversationMessage(**msg) for msg in messages],
        )

    @router.post("/client-info", response_model=ClientMetadataResponse)
    async def get_client_info(request: ClientInfoRequest):
        """
        Get client/hospital information

        Args:
            request: ClientInfoRequest with client_id

        Returns:
            Client metadata
        """
        logger.info(f"Fetching client info: {request.client_id}")

        metadata = client_manager.get_client_metadata(request.client_id)

        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found",
            )

        return ClientMetadataResponse(**metadata)

    @router.get("/clients")
    async def list_clients():
        """
        List all available clients

        Returns:
            List of client IDs and metadata
        """
        logger.info("Listing all clients")

        client_ids = client_manager.list_clients()
        clients = []

        for client_id in client_ids:
            metadata = client_manager.get_client_metadata(client_id)
            if metadata:
                clients.append({
                    "id": client_id,
                    "metadata": metadata,
                })

        return {"clients": clients, "count": len(clients)}

    return router
