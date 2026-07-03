from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.knowledge import KnowledgeContextBuilder, KnowledgeLoader
from app.services import (
    SheetsService,
    GroqService,
    PromptManager,
    ClientManager,
    ExcelService,
    CampaignService,
    OutcomeService,
    ConversationAnalyzer,
    CampaignOrchestrator,
    LocalTrainingService,
    DoctorService,
    BookingService,
    ConversationOrchestrator,
)
from app.routes import (
    create_campaigns_router,
    create_training_router,
    create_conversation_router,
)
from app.utils import get_logger

logger = get_logger(__name__)

sheets_service = None
groq_service = None
prompt_manager = None
client_manager = None
excel_service = None
campaign_service = None
campaign_orchestrator = None
training_service = None
conversation_orchestrator = None
knowledge_loader = None
knowledge_context_builder = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global sheets_service, groq_service, prompt_manager, client_manager
    global excel_service, campaign_service, campaign_orchestrator, training_service
    global conversation_orchestrator, knowledge_loader, knowledge_context_builder

    # Startup
    logger.info("Starting up application...")
    try:
        # Initialize Google Sheets service. On Render, prefer
        # GOOGLE_SERVICE_ACCOUNT_JSON so secrets do not need a mounted file.
        try:
            sheets_service = SheetsService(
                credentials_path=settings.GOOGLE_SHEETS_CREDENTIALS_PATH,
                credentials_json=settings.GOOGLE_SERVICE_ACCOUNT_JSON,
                sheet_name=settings.GOOGLE_SHEET_NAME,
                spreadsheet_id=settings.GOOGLE_SHEET_ID,
            )
            logger.info("Google Sheets service initialized successfully")
        except Exception as exc:
            if not settings.ALLOW_SHEETS_FALLBACK:
                raise
            sheets_service = None
            logger.warning(
                "Google Sheets service unavailable; starting without sheet-backed routes",
                extra={"extra_data": {"error": str(exc)}},
            )

        # Initialize Groq service
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY not set - AI features will be disabled")
        else:
            groq_service = GroqService(
                api_key=settings.GROQ_API_KEY,
                model=settings.GROQ_MODEL,
            )
            logger.info("Groq service initialized successfully")

        prompt_manager = PromptManager()
        logger.info("Prompt manager initialized")

        client_manager = ClientManager()
        logger.info("Client manager initialized")

        knowledge_path = Path(__file__).resolve().parent / "knowledge_base"
        knowledge_loader = KnowledgeLoader(knowledge_path)
        knowledge_index = knowledge_loader.load()
        knowledge_context_builder = KnowledgeContextBuilder(knowledge_index)
        logger.info("Knowledge context builder initialized")

        if sheets_service:
            doctor_service = DoctorService(sheets_service)
            booking_service = BookingService(sheets_service, doctor_service)
            conversation_orchestrator = ConversationOrchestrator(
                groq_service=groq_service,
                prompt_manager=prompt_manager,
                client_manager=client_manager,
                booking_service=booking_service,
                doctor_service=doctor_service,
                knowledge_context_builder=knowledge_context_builder,
            )
            app.include_router(create_conversation_router(conversation_orchestrator, client_manager))
            logger.info("Conversation routes included")

            excel_service = ExcelService(
                sheets_service=sheets_service,
                sheet_title=settings.CAMPAIGN_SHEET_TITLE,
            )
            campaign_service = CampaignService(excel_service)
            logger.info("Campaign services initialized")

        if sheets_service:
            outcome_service = OutcomeService()
            analyzer = ConversationAnalyzer(
                llm_service=groq_service,
                outcome_service=outcome_service,
            )
            campaign_orchestrator = CampaignOrchestrator(
                campaign_service=campaign_service,
                excel_service=excel_service,
                analyzer=analyzer,
            )
            training_service = LocalTrainingService(
                campaign_service=campaign_service,
                orchestrator=campaign_orchestrator,
                prompt_manager=prompt_manager,
                client_manager=client_manager,
                llm_service=groq_service,
            )
            logger.info("Campaign orchestrator and local training service initialized")

        if campaign_service and campaign_orchestrator:
            app.include_router(create_campaigns_router(campaign_service, campaign_orchestrator))
            logger.info("Campaign routes included")

        if training_service:
            app.include_router(create_training_router(training_service))
            logger.info("Local training routes included")

    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")
    if groq_service:
        await groq_service.close()
        logger.info("Groq service closed")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local AI campaign training backend for hospital outreach",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
        },
    )


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    logger.info("Health check called")
    return {"status": "ok"}


@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Hospital AI Campaign Calling Platform",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "features": [
            "Campaign lead selection",
            "Local AI conversation training",
            "Conversation transcript analysis",
            "Outcome classification",
            "Excel campaign updates",
            "Multi-client support",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
