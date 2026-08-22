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
    GEMINI_API_KEYS_STR: Optional[str] = os.getenv("GEMINI_API_KEYS", None)
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
    
    @property
    def api_keys(self) -> list[str]:
        keys = []
        if self.GEMINI_API_KEYS_STR:
            keys.extend([k.strip() for k in self.GEMINI_API_KEYS_STR.split(",") if k.strip()])
        if self.GEMINI_API_KEY and self.GEMINI_API_KEY not in keys:
            keys.append(self.GEMINI_API_KEY)
        return keys

    @property
    def fallback_models(self) -> list[str]:
        # Priority order of active Gemini models for OCR data extraction
        default_chain = [
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-2.5-pro",
            "gemini-3.7-flash",
            "gemini-3.5-flash",
            "gemini-pro-latest"
        ]
        if self.GEMINI_MODEL_NAME and self.GEMINI_MODEL_NAME not in default_chain:
            return [self.GEMINI_MODEL_NAME] + default_chain
        # Ensure preferred model is first
        chain = [self.GEMINI_MODEL_NAME] + [m for m in default_chain if m != self.GEMINI_MODEL_NAME]
        return chain

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./invoices.db"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

