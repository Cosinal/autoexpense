from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AutoExpense"
    DEBUG: bool = True

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Gmail API
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REFRESH_TOKEN: str = ""
    INTAKE_EMAIL: str = ""

    # OCR
    TESSERACT_CMD: str = "/usr/local/bin/tesseract"  # macOS default

    # Storage
    RECEIPT_BUCKET: str = "receipts"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
