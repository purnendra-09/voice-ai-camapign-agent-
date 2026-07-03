from fastapi import APIRouter, HTTPException, status
from app.models import CheckDoctorRequest, DoctorResponse, DoctorNotFoundResponse
from app.services import SheetsService, DoctorService
from app.utils import get_logger

logger = get_logger(__name__)


def create_doctors_router(sheets_service: SheetsService) -> APIRouter:
    """Create doctors router with all endpoints"""

    router = APIRouter(prefix="/doctors", tags=["doctors"])
    doctor_service = DoctorService(sheets_service)

    @router.post("/check", response_model=DoctorResponse | DoctorNotFoundResponse)
    async def check_doctor_availability(request: CheckDoctorRequest):
        """
        Check doctor availability

        Args:
            request: CheckDoctorRequest with doctor_name

        Returns:
            Doctor availability status and details
        """
        logger.info(f"Checking availability for doctor: {request.doctor_name}")

        result = doctor_service.check_availability(request.doctor_name)

        if not result.get("available"):
            return DoctorNotFoundResponse()

        return DoctorResponse(
            doctor_name=result.get("doctor_name"),
            available=True,
            time=result.get("time"),
            department=result.get("department"),
        )

    @router.get("/all")
    async def get_all_doctors():
        """Get all doctors from the database"""
        logger.info("Fetching all doctors")

        doctors = doctor_service.get_all_doctors()

        return {"doctors": doctors, "count": len(doctors)}

    return router
