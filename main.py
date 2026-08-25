import logging
import os

from flask import Flask, jsonify, request, send_from_directory

from api.whatsapp_webhook import WhatsAppWebhookAPI
from config.settings import settings, validate_settings
from graph import SwasthMitraGraph
from utils.ngrok import start_ngrok_tunnel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

validate_settings()

app = Flask(__name__)
graph = SwasthMitraGraph()
whatsapp = WhatsAppWebhookAPI(graph)

os.makedirs(settings.IMAGE_DIR, exist_ok=True)


@app.route("/webhook", methods=["GET"])
def verify():
    return whatsapp.verify_webhook(request)


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        return whatsapp.handle_message(request)
    except Exception as exc:
        logger.exception("Webhook failed: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": settings.APP_NAME,
        "model": settings.GEMINI_MODEL,
        "twilio": settings.twilio_configured,
    })


@app.route("/generated/<path:filename>")
def serve_image(filename):
    return send_from_directory(settings.IMAGE_DIR, filename)


@app.route("/chat", methods=["POST"])
def local_chat():
    """Local test endpoint — no Twilio needed."""
    data = request.get_json(force=True)
    message = data.get("message", "")
    user_id = data.get("user_id", "local-test-user")
    if not message:
        return jsonify({"error": "message required"}), 400

    result = graph.run(user_input=message, user_id=user_id)
    return jsonify({
        "reply": result["reply"],
        "image_url": result.get("generated_image_url", ""),
    })


if __name__ == "__main__":
    logger.info("Starting %s on %s:%s", settings.APP_NAME, settings.HOST, settings.PORT)
    public_url = start_ngrok_tunnel()
    if public_url:
        logger.info("Set Twilio webhook to: %s/webhook", public_url)
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG, use_reloader=False)
