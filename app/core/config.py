import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Based Multi Invoice Processing"
    API_V1_STR: str = "/api/v1"
    
    # Google Sheets Config
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json")
    GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "your_google_sheet_id_here")
    
    # AI API Config
    AI_API_KEY: str = os.getenv("AI_API_KEY", "your_ai_api_key_here")

    # Gemini AI Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./invoices.db"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
