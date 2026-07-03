from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class AppointmentBase(BaseModel):
    """Base appointment model"""
    patient_name: str = Field(..., min_length=1, description="Patient's full name")
    phone: str = Field(..., pattern=r"^\d{10}$", description="10-digit phone number")
    doctor_name: str = Field(..., min_length=1, description="Doctor's name")
    date: str = Field(..., description="Appointment date (YYYY-MM-DD format)")
    time: str = Field(..., min_length=1, description="Appointment time")

    @validator("date")
    def validate_date(cls, v):
        """Validate date format"""
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")

    @validator("phone")
    def validate_phone(cls, v):
        """Validate phone number"""
        if not v.isdigit() or len(v) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return v


class BookAppointmentRequest(AppointmentBase):
    """Request model for booking appointment"""
    pass


class AppointmentSuccessResponse(BaseModel):
    """Success response for appointment booking"""
    status: str = "confirmed"
    doctor_name: str
    date: str
    time: str
    patient_name: Optional[str] = None


class AppointmentFailureResponse(BaseModel):
    """Failure response for appointment booking"""
    status: str = "failed"
    message: str


class AppointmentRecord(BaseModel):
    """Complete appointment record from sheets"""
    patient_name: str
    phone: str
    doctor_name: str
    date: str
    time: str
    created_at: Optional[str] = None
