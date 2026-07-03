from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Application
    APP_NAME: str = "Hospital AI Campaign Calling Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS_PATH: str = "app/credentials/google-service-account.json"
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None
    GOOGLE_SHEET_ID: Optional[str] = "1_C4jx5XFMKErjwnb0ZVKtMakfhnK4wNVAd0v4amsEvo"

    GOOGLE_SHEET_NAME: str = "Hospital_Campaigns"
    CAMPAIGN_SHEET_TITLE: str = "Hospital Campaign"

    # AI API. Groq and xAI both expose OpenAI-compatible chat endpoints.
    AI_PROVIDER: str = "groq"
    AI_BASE_URL: Optional[str] = None
    AI_API_KEY: Optional[str] = None
    AI_MODEL: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    XAI_API_KEY: Optional[str] = None
    GROK_API_KEY: Optional[str] = None
    GROK_MODEL: str = "grok-2-latest"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Local fallback keeps health checks and non-AI endpoints alive on Render
    # before Google Sheets credentials are mounted.
    ALLOW_SHEETS_FALLBACK: bool = True

    # CORS
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = False
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]

    # AI Configuration
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 1000

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str) and value.lower() in {"release", "production", "prod"}:
            return False
        return value

    @field_validator("CORS_ORIGINS", "CORS_METHODS", "CORS_HEADERS", mode="before")
    @classmethod
    def parse_list_values(cls, value):
        if isinstance(value, str):
            import json

            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return [item.strip() for item in value.split(",") if item.strip()]
        return value

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
