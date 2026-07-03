from pydantic import BaseModel, Field
from typing import Optional


class DoctorBase(BaseModel):
    """Base doctor model"""
    doctor_name: str = Field(..., min_length=1, description="Doctor's full name")
    department: str = Field(..., min_length=1, description="Medical department")
    timings: str = Field(..., min_length=1, description="Available timings")
    available: str = Field(default="Yes", description="Availability status")


class DoctorResponse(BaseModel):
    """Doctor availability response model"""
    doctor_name: str
    available: bool
    time: Optional[str] = None
    department: Optional[str] = None


class DoctorNotFoundResponse(BaseModel):
    """Response when doctor not found"""
    available: bool = False
    message: str = "Doctor not found"


class CheckDoctorRequest(BaseModel):
    """Request model for checking doctor availability"""
    doctor_name: str = Field(..., min_length=1, description="Doctor's name to check")
