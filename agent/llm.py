from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import settings


def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.4,
        convert_system_message_to_human=True,
    )
