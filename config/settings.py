from pydantic import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "SwasthMitra-LangGraph"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 5000))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Twilio settings
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "")
    TWILIO_VOICE_NUMBER: str = os.getenv("TWILIO_VOICE_NUMBER", "")
    EMERGENCY_CONTACT_NUMBER: str = os.getenv("EMERGENCY_CONTACT_NUMBER", "")
    
    # AI/ML settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # External API settings
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    CLIPDROP_API_KEY: str = os.getenv("CLIPDROP_API_KEY", "")
    
    # Service settings
    MAX_HISTORY_LENGTH: int = int(os.getenv("MAX_HISTORY_LENGTH", 12))
    CHAT_HISTORY_FILE: str = os.getenv("CHAT_HISTORY_FILE", "data/chat_histories.json")
    IMAGE_DIR: str = os.getenv("IMAGE_DIR", "generated_images")
    
    # Language settings
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")
    SUPPORTED_LANGUAGES: list = ["en", "or"]  # English and Odia
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create a settings instance
settings = Settings()

# Validate that critical settings are present
def validate_settings():
    missing_keys = []
    
    if not settings.TWILIO_ACCOUNT_SID:
        missing_keys.append("TWILIO_ACCOUNT_SID")
    if not settings.TWILIO_AUTH_TOKEN:
        missing_keys.append("TWILIO_AUTH_TOKEN")
    if not settings.GEMINI_API_KEY:
        missing_keys.append("GEMINI_API_KEY")
    
    if missing_keys:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")

# Validate settings on import
validate_settings()