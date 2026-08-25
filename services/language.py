import logging

from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


class LanguageService:
    """Detect Odia/English and translate for processing."""

    @staticmethod
    def detect(text: str) -> str:
        if not text:
            return "en"
        odia_chars = [c for c in text if "\u0B00" <= c <= "\u0B7F"]
        if len(odia_chars) / max(len(text), 1) > 0.1:
            return "or"
        return "en"

    @staticmethod
    def to_english(text: str) -> str:
        try:
            return GoogleTranslator(source="or", target="en").translate(text)
        except Exception as exc:
            logger.warning("Translation to English failed: %s", exc)
            return text

    @staticmethod
    def to_odia(text: str) -> str:
        try:
            return GoogleTranslator(source="en", target="or").translate(text)
        except Exception as exc:
            logger.warning("Translation to Odia failed: %s", exc)
            return text

    def prepare_input(self, text: str) -> tuple[str, str]:
        lang = self.detect(text)
        if lang == "or":
            return self.to_english(text), lang
        return text, lang

    def localize_output(self, text: str, lang: str) -> str:
        if lang == "or":
            return self.to_odia(text)
        return text
