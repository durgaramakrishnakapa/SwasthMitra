from flask import Flask, request, jsonify
from graph import SwasthMitraGraph
from api.whatsapp_webhook import WhatsAppWebhookAPI
from config.settings import settings
import logging
from services.chat_history_service import ChatHistoryService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize services
chat_history_service = ChatHistoryService()

# Initialize the LangGraph workflow
swasth_mitra_graph = SwasthMitraGraph()

# Initialize WhatsApp webhook handler
whatsapp_api = WhatsAppWebhookAPI(swasth_mitra_graph)


@app.route('/webhook', methods=['GET'])
def verify():
    """
    Verify webhook endpoint for WhatsApp Business API
    """
    return whatsapp_api.verify_webhook(request)


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Main webhook endpoint for receiving WhatsApp messages
    """
    try:
        result = whatsapp_api.handle_message(request)
        return result
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({"status": "healthy", "service": "SwasthMitra-LangGraph"})


if __name__ == "__main__":
    logger.info("Starting SwasthMitra-LangGraph service...")
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)