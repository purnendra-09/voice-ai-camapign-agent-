import re
from datetime import datetime
from typing import Optional


def validate_phone(phone: str) -> bool:
    """Validate Indian phone number format (10 digits)"""
    pattern = r"^\d{10}$"
    return bool(re.match(pattern, phone))


def validate_date(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_date_not_past(date_str: str) -> bool:
    """Validate that date is not in the past"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.date() >= datetime.now().date()
    except ValueError:
        return False


def validate_doctor_name(name: str) -> bool:
    """Validate doctor name (non-empty string)"""
    return isinstance(name, str) and len(name.strip()) > 0


def validate_patient_name(name: str) -> bool:
    """Validate patient name (non-empty string)"""
    return isinstance(name, str) and len(name.strip()) > 0


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize and truncate string input"""
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def validate_required_fields(data: dict, required_fields: list) -> tuple[bool, Optional[str]]:
    """Validate that all required fields are present and non-empty"""
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    return True, None
