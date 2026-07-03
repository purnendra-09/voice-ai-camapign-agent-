from typing import Dict, Optional, List
from app.utils import get_logger, validate_doctor_name
from app.services.sheets_service import SheetsService

logger = get_logger(__name__)


class DoctorService:
    """Service for doctor-related operations"""

    def __init__(self, sheets_service: SheetsService):
        """
        Initialize Doctor Service

        Args:
            sheets_service: Instance of SheetsService
        """
        self.sheets_service = sheets_service
        self.doctors_sheet_title = "Doctors"

    def check_availability(self, doctor_name: str) -> Dict:
        """
        Check doctor availability

        Args:
            doctor_name: Name of the doctor to check

        Returns:
            Dictionary with availability status and doctor info
        """
        try:
            if not validate_doctor_name(doctor_name):
                logger.error(f"Invalid doctor name: {doctor_name}")
                return {"available": False, "message": "Invalid doctor name"}

            doctors = self.sheets_service.read_all_records(self.doctors_sheet_title)

            for doctor in doctors:
                if doctor.get("doctor_name", "").lower() == doctor_name.lower():
                    available_status = doctor.get("available", "").lower() == "yes"

                    return {
                        "doctor_name": doctor.get("doctor_name"),
                        "available": available_status,
                        "time": doctor.get("timings", ""),
                        "department": doctor.get("department", ""),
                    }

            logger.warning(f"Doctor not found: {doctor_name}")
            return {"available": False, "message": "Doctor not found"}

        except Exception as e:
            logger.error(f"Error checking doctor availability: {str(e)}")
            return {"available": False, "message": "Error checking availability"}

    def get_all_doctors(self) -> List[Dict]:
        """
        Get all doctors from the sheet

        Returns:
            List of doctor records
        """
        try:
            return self.sheets_service.read_all_records(self.doctors_sheet_title)
        except Exception as e:
            logger.error(f"Error fetching all doctors: {str(e)}")
            return []

    def doctor_exists(self, doctor_name: str) -> bool:
        """
        Check if a doctor exists in the database

        Args:
            doctor_name: Name of the doctor

        Returns:
            True if doctor exists, False otherwise
        """
        try:
            doctors = self.sheets_service.read_all_records(self.doctors_sheet_title)
            return any(
                doctor.get("doctor_name", "").lower() == doctor_name.lower()
                for doctor in doctors
            )
        except Exception as e:
            logger.error(f"Error checking if doctor exists: {str(e)}")
            return False

    def is_slot_available(self, doctor_name: str, date: str, time: str) -> bool:
        """
        Check if a specific slot is available for a doctor
        (Note: This is a simplified implementation. In production, you might have
         separate slot management)

        Args:
            doctor_name: Name of the doctor
            date: Appointment date
            time: Appointment time

        Returns:
            True if slot is available, False otherwise
        """
        try:
            doctor_data = self.check_availability(doctor_name)
            if not doctor_data.get("available"):
                logger.warning(f"Doctor {doctor_name} not available")
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking slot availability: {str(e)}")
            return False
