from datetime import datetime
from typing import Dict, Tuple
from app.utils import (
    get_logger,
    validate_phone,
    validate_date,
    validate_date_not_past,
    validate_patient_name,
    validate_doctor_name,
)
from app.services.sheets_service import SheetsService
from app.services.doctor_service import DoctorService

logger = get_logger(__name__)


class BookingService:
    """Service for appointment booking operations"""

    def __init__(self, sheets_service: SheetsService, doctor_service: DoctorService):
        """
        Initialize Booking Service

        Args:
            sheets_service: Instance of SheetsService
            doctor_service: Instance of DoctorService
        """
        self.sheets_service = sheets_service
        self.doctor_service = doctor_service
        self.appointments_sheet_title = "Appointments"

    def validate_booking_request(self, patient_name: str, phone: str, doctor_name: str, date: str, time: str) -> Tuple[bool, str]:
        """
        Validate all fields for appointment booking

        Args:
            patient_name: Name of the patient
            phone: Phone number (10 digits)
            doctor_name: Name of the doctor
            date: Appointment date (YYYY-MM-DD)
            time: Appointment time

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate patient name
        if not validate_patient_name(patient_name):
            error_msg = "Invalid patient name"
            logger.warning(f"Validation failed: {error_msg}")
            return False, error_msg

        # Validate phone
        if not validate_phone(phone):
            error_msg = "Phone number must be 10 digits"
            logger.warning(f"Validation failed: {error_msg}")
            return False, error_msg

        # Validate doctor name
        if not validate_doctor_name(doctor_name):
            error_msg = "Invalid doctor name"
            logger.warning(f"Validation failed: {error_msg}")
            return False, error_msg

        # Validate date format
        if not validate_date(date):
            error_msg = "Date must be in YYYY-MM-DD format"
            logger.warning(f"Validation failed: {error_msg}")
            return False, error_msg

        # Validate date is not in past
        if not validate_date_not_past(date):
            error_msg = "Cannot book appointment for past date"
            logger.warning(f"Validation failed: {error_msg}")
            return False, error_msg

        # Validate time
        if not time or len(time.strip()) == 0:
            error_msg = "Time is required"
            logger.warning(f"Validation failed: {error_msg}")
            return False, error_msg

        return True, ""

    def check_duplicate_booking(self, patient_name: str, doctor_name: str, date: str, time: str) -> bool:
        """
        Check if a duplicate booking already exists

        Args:
            patient_name: Name of the patient
            doctor_name: Name of the doctor
            date: Appointment date
            time: Appointment time

        Returns:
            True if duplicate exists, False otherwise
        """
        try:
            search_dict = {
                "patient_name": patient_name,
                "doctor_name": doctor_name,
                "date": date,
                "time": time,
            }
            is_duplicate = self.sheets_service.check_duplicate(
                self.appointments_sheet_title, search_dict
            )
            if is_duplicate:
                logger.warning(
                    f"Duplicate booking detected for {patient_name} with {doctor_name} on {date} at {time}"
                )
            return is_duplicate
        except Exception as e:
            logger.error(f"Error checking duplicate booking: {str(e)}")
            return False

    def book_appointment(
        self, patient_name: str, phone: str, doctor_name: str, date: str, time: str
    ) -> Dict:
        """
        Book an appointment with complete validation

        Args:
            patient_name: Name of the patient
            phone: Phone number
            doctor_name: Name of the doctor
            date: Appointment date (YYYY-MM-DD)
            time: Appointment time

        Returns:
            Dictionary with booking status and details
        """
        try:
            # Step 1: Validate all fields
            is_valid, error_msg = self.validate_booking_request(
                patient_name, phone, doctor_name, date, time
            )
            if not is_valid:
                return {"status": "failed", "message": error_msg}

            # Step 2: Check if doctor exists
            if not self.doctor_service.doctor_exists(doctor_name):
                error_msg = "Doctor not found"
                logger.warning(error_msg)
                return {"status": "failed", "message": error_msg}

            # Step 3: Check if doctor is available
            if not self.doctor_service.is_slot_available(doctor_name, date, time):
                error_msg = "Slot unavailable"
                logger.warning(error_msg)
                return {"status": "failed", "message": error_msg}

            # Step 4: Check for duplicate booking
            if self.check_duplicate_booking(patient_name, doctor_name, date, time):
                error_msg = "Appointment already booked for this slot"
                logger.warning(error_msg)
                return {"status": "failed", "message": error_msg}

            # Step 5: Write appointment to Google Sheets
            created_at = datetime.utcnow().isoformat()
            row_data = [patient_name, phone, doctor_name, date, time, created_at]

            success = self.sheets_service.write_row(self.appointments_sheet_title, row_data)

            if not success:
                error_msg = "Failed to save appointment"
                logger.error(error_msg)
                return {"status": "failed", "message": error_msg}

            # Step 6: Return success response
            logger.info(f"Appointment booked successfully: {patient_name} with {doctor_name}")
            return {
                "status": "confirmed",
                "doctor_name": doctor_name,
                "date": date,
                "time": time,
                "patient_name": patient_name,
            }

        except Exception as e:
            error_msg = "Internal server error"
            logger.error(f"Error booking appointment: {str(e)}")
            return {"status": "failed", "message": error_msg}

    def get_all_appointments(self) -> list:
        """
        Get all appointments from the sheet

        Returns:
            List of appointment records
        """
        try:
            return self.sheets_service.read_all_records(self.appointments_sheet_title)
        except Exception as e:
            logger.error(f"Error fetching all appointments: {str(e)}")
            return []
