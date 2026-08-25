from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

    APP_NAME: str = "SwasthMitra"
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    DEBUG: bool = False

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""
    TWILIO_VOICE_NUMBER: str = ""
    EMERGENCY_CONTACT_NUMBER: str = ""

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GROQ_API_KEY: str = ""

    TAVILY_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    CLIPDROP_API_KEY: str = ""

    NGROK_AUTHTOKEN: str = ""
    NGROK_DOMAIN: str = ""

    MAX_HISTORY_TURNS: int = 16
    CHAT_HISTORY_FILE: str = "data/chat_histories.json"
    PROFILE_FILE: str = "data/user_profiles.json"
    IMAGE_DIR: str = "generated_images"
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: list[str] = ["en", "or"]

    @property
    def twilio_configured(self) -> bool:
        return bool(self.TWILIO_ACCOUNT_SID and self.TWILIO_AUTH_TOKEN and self.TWILIO_WHATSAPP_NUMBER)


settings = Settings()


def validate_settings() -> None:
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required")
