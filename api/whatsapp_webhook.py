import logging
import re

from flask import jsonify

from config.settings import settings
from services.language import LanguageService

logger = logging.getLogger(__name__)


class WhatsAppWebhookAPI:
    """Handles incoming WhatsApp messages via Twilio webhook."""

    def __init__(self, graph) -> None:
        self.graph = graph
        self.language = LanguageService()

    def verify_webhook(self, request):
        return "success"

    def handle_message(self, request):
        try:
            original_msg = (request.values.get("Body") or "").strip()
            from_number = request.values.get("From", "local-user")
            num_media = int(request.values.get("NumMedia", 0))

            if num_media > 0:
                media_type = (request.values.get("MediaContentType0") or "").lower()
                media_url = request.values.get("MediaUrl0", "")
                user_message = f"Please analyze my medical {media_type.split('/')[0]} report."
                translated, lang = self.language.prepare_input(user_message)

                result = self.graph.run(
                    user_input=translated,
                    user_id=from_number,
                    media_url=media_url,
                    media_type=media_type,
                )
                reply = self.language.localize_output(result["reply"], lang)
                image_url = result.get("generated_image_url") or self._extract_image(reply)
                self._send(reply, from_number, image_url)
                return jsonify({"status": "media_processed"})

            if not original_msg:
                return jsonify({"status": "empty"})

            translated, lang = self.language.prepare_input(original_msg)
            result = self.graph.run(user_input=translated, user_id=from_number)
            reply = self.language.localize_output(result["reply"], lang)
            image_url = result.get("generated_image_url") or self._extract_image(reply)
            self._send(reply, from_number, image_url)
            return jsonify({"status": "ok"})

        except Exception as exc:
            logger.exception("Webhook error: %s", exc)
            return jsonify({"status": "error", "message": str(exc)}), 500

    def _send(self, body: str, to_number: str, media_url: str | None = None) -> None:
        if not settings.twilio_configured:
            logger.info("[Twilio not configured] To %s: %s", to_number, body[:200])
            if media_url:
                logger.info("[Twilio not configured] Media: %s", media_url)
            return

        try:
            from twilio.rest import Client

            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            max_len = 1600

            if media_url:
                client.messages.create(
                    body=body[:max_len],
                    from_=settings.TWILIO_WHATSAPP_NUMBER,
                    to=to_number,
                    media_url=[media_url],
                )
                return

            if len(body) <= max_len:
                client.messages.create(
                    body=body,
                    from_=settings.TWILIO_WHATSAPP_NUMBER,
                    to=to_number,
                )
            else:
                chunks = [body[i : i + max_len - 20] for i in range(0, len(body), max_len - 20)]
                for i, chunk in enumerate(chunks):
                    client.messages.create(
                        body=f"({i + 1}/{len(chunks)})\n{chunk}",
                        from_=settings.TWILIO_WHATSAPP_NUMBER,
                        to=to_number,
                    )
        except Exception as exc:
            logger.error("Failed to send WhatsApp message: %s", exc)

    @staticmethod
    def _extract_image(text: str) -> str | None:
        match = re.search(r"IMAGE_URL:(\S+)", text)
        return match.group(1) if match else None
