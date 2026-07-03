import json

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import List, Dict, Optional, Any
from app.utils import get_logger

logger = get_logger(__name__)


class SheetsService:
    """Service for Google Sheets operations"""

    HEADER_ALIASES = {
        "doctor_name": "doctor_name",
        "doctor name": "doctor_name",
        "doctorname": "doctor_name",
        "department": "department",
        "timings": "timings",
        "timing": "timings",
        "available": "available",
        "availability": "available",
        "avaliability": "available",
        "patient_name": "patient_name",
        "patient name": "patient_name",
        "patientname": "patient_name",
        "phone": "phone",
        "date": "date",
        "time": "time",
        "created_at": "created_at",
        "created at": "created_at",
        "createdat": "created_at",
        "patient": "patient_name",
        "patient_id": "patient_id",
        "patient id": "patient_id",
        "patientid": "patient_id",
        "phone_number": "phone_number",
        "phone number": "phone_number",
        "phonenumber": "phone_number",
        "language": "language",
        "campaign": "campaign",
        "campaign_name": "campaign",
        "campaign name": "campaign",
        "campaignname": "campaign",
        "status": "status",
        "priority": "priority",
        "call_attempts": "call_attempts",
        "call attempts": "call_attempts",
        "callattempts": "call_attempts",
        "last_call_time": "last_call_time",
        "last call time": "last_call_time",
        "lastcalltime": "last_call_time",
        "outcome": "outcome",
        "summary": "summary",
        "next_action": "next_action",
        "next action": "next_action",
        "nextaction": "next_action",
        "next_call_time": "next_call_time",
        "next call time": "next_call_time",
        "nextcalltime": "next_call_time",
        "assigned_agent": "assigned_agent",
        "assigned agent": "assigned_agent",
        "assignedagent": "assigned_agent",
        "notes": "notes",
    }

    def __init__(
        self,
        credentials_path: str,
        sheet_name: str,
        spreadsheet_id: Optional[str] = None,
        credentials_json: Optional[str] = None,
    ):
        """
        Initialize Sheets Service with Google Service Account credentials

        Args:
            credentials_path: Path to Google Service Account JSON
            sheet_name: Name of the Google Sheet
            spreadsheet_id: Optional Google Sheet ID from the spreadsheet URL
        """
        self.credentials_path = credentials_path
        self.credentials_json = credentials_json
        self.sheet_name = sheet_name
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.spreadsheet = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize gspread client with service account credentials"""
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ]
            if self.credentials_json:
                credentials_info = json.loads(self.credentials_json)
                credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                    credentials_info, scope
                )
            else:
                credentials = ServiceAccountCredentials.from_json_keyfile_name(
                    self.credentials_path, scope
                )
            self.client = gspread.authorize(credentials)
            if self.spreadsheet_id:
                self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            else:
                self.spreadsheet = self.client.open(self.sheet_name)
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {str(e)}")
            raise

    def get_sheet(self, sheet_title: str) -> Optional[Any]:
        """
        Get a specific worksheet by title

        Args:
            sheet_title: Title of the worksheet

        Returns:
            Worksheet object or None if not found
        """
        try:
            return self.spreadsheet.worksheet(sheet_title)
        except gspread.exceptions.WorksheetNotFound:
            normalized_title = sheet_title.strip().lower()
            for worksheet in self.spreadsheet.worksheets():
                if worksheet.title.strip().lower() == normalized_title:
                    return worksheet
            logger.error(f"Worksheet '{sheet_title}' not found")
            return None
        except Exception as e:
            logger.error(f"Error accessing worksheet '{sheet_title}': {str(e)}")
            return None

    def read_all_records(self, sheet_title: str) -> List[Dict[str, Any]]:
        """
        Read all records from a worksheet

        Args:
            sheet_title: Title of the worksheet

        Returns:
            List of dictionaries representing rows
        """
        try:
            worksheet = self.get_sheet(sheet_title)
            if not worksheet:
                return []
            values = worksheet.get_all_values()
            if len(values) < 2:
                return []

            headers = [self._normalize_header(header) for header in values[0]]
            records = []
            for row in values[1:]:
                if not any(cell.strip() for cell in row):
                    continue
                record = {}
                for index, header in enumerate(headers):
                    if not header:
                        continue
                    record[header] = row[index] if index < len(row) else ""
                records.append(record)
            return records
        except Exception as e:
            logger.error(f"Error reading records from '{sheet_title}': {str(e)}")
            return []

    def _normalize_header(self, header: str) -> str:
        """Normalize Google Sheet headers into backend field names."""
        normalized = header.strip().lower().replace("-", "_")
        normalized = "_".join(normalized.split())
        return self.HEADER_ALIASES.get(normalized, normalized)

    def write_row(self, sheet_title: str, row_data: List[Any]) -> bool:
        """
        Append a row to a worksheet

        Args:
            sheet_title: Title of the worksheet
            row_data: List of values to append

        Returns:
            True if successful, False otherwise
        """
        try:
            worksheet = self.get_sheet(sheet_title)
            if not worksheet:
                return False
            worksheet.append_row(row_data)
            logger.info(f"Row appended to '{sheet_title}': {row_data}")
            return True
        except Exception as e:
            logger.error(f"Error writing to '{sheet_title}': {str(e)}")
            return False

    def find_row(self, sheet_title: str, search_value: str, column_index: int = 1) -> Optional[Dict[str, Any]]:
        """
        Find first row matching a search value in specific column

        Args:
            sheet_title: Title of the worksheet
            search_value: Value to search for
            column_index: Column index to search (1-based)

        Returns:
            Row as dictionary or None if not found
        """
        try:
            records = self.read_all_records(sheet_title)
            for record in records:
                if list(record.values())[column_index - 1] == search_value:
                    return record
            return None
        except Exception as e:
            logger.error(f"Error finding row in '{sheet_title}': {str(e)}")
            return None

    def check_duplicate(self, sheet_title: str, search_dict: Dict[str, str]) -> bool:
        """
        Check if a record with matching fields already exists

        Args:
            sheet_title: Title of the worksheet
            search_dict: Dictionary of field:value pairs to match

        Returns:
            True if duplicate found, False otherwise
        """
        try:
            records = self.read_all_records(sheet_title)
            for record in records:
                match = all(record.get(key) == value for key, value in search_dict.items())
                if match:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking duplicate in '{sheet_title}': {str(e)}")
            return False

    def get_column_values(self, sheet_title: str, column_index: int) -> List[str]:
        """
        Get all values from a specific column

        Args:
            sheet_title: Title of the worksheet
            column_index: Column index (1-based)

        Returns:
            List of column values
        """
        try:
            worksheet = self.get_sheet(sheet_title)
            if not worksheet:
                return []
            return worksheet.col_values(column_index)
        except Exception as e:
            logger.error(f"Error reading column from '{sheet_title}': {str(e)}")
            return []
