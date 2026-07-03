from fastapi import APIRouter, HTTPException, status
from app.models import (
    BookAppointmentRequest,
    AppointmentSuccessResponse,
    AppointmentFailureResponse,
)
from app.services import SheetsService, DoctorService, BookingService
from app.utils import get_logger

logger = get_logger(__name__)


def create_appointments_router(sheets_service: SheetsService) -> APIRouter:
    """Create appointments router with all endpoints"""

    router = APIRouter(prefix="/appointments", tags=["appointments"])
    doctor_service = DoctorService(sheets_service)
    booking_service = BookingService(sheets_service, doctor_service)

    @router.post("/book", response_model=AppointmentSuccessResponse | AppointmentFailureResponse)
    async def book_appointment(request: BookAppointmentRequest):
        """
        Book an appointment

        Args:
            request: BookAppointmentRequest with patient and appointment details

        Returns:
            Appointment confirmation or failure response
        """
        logger.info(f"Booking appointment for patient: {request.patient_name}")

        result = booking_service.book_appointment(
            patient_name=request.patient_name,
            phone=request.phone,
            doctor_name=request.doctor_name,
            date=request.date,
            time=request.time,
        )

        if result.get("status") == "failed":
            return AppointmentFailureResponse(message=result.get("message", "Booking failed"))

        return AppointmentSuccessResponse(
            status="confirmed",
            doctor_name=result.get("doctor_name"),
            date=result.get("date"),
            time=result.get("time"),
            patient_name=result.get("patient_name"),
        )

    @router.get("/all")
    async def get_all_appointments():
        """Get all appointments from the database"""
        logger.info("Fetching all appointments")

        appointments = booking_service.get_all_appointments()

        return {"appointments": appointments, "count": len(appointments)}

    return router
