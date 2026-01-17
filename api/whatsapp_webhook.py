from flask import request, jsonify
import json
import logging
from typing import Dict, Any
from deep_translator import GoogleTranslator
from utils.conversation_manager import ConversationManager
from config.settings import settings
from langchain_core.messages import HumanMessage
from services.interactive_menu_service import InteractiveMenuService
from services.chat_history_service import ChatHistoryService

logger = logging.getLogger(__name__)

class WhatsAppWebhookAPI:
    """
    Handles WhatsApp webhook requests from Twilio
    """
    
    def __init__(self, swasth_mitra_graph):
        self.graph = swasth_mitra_graph
        self.conversation_manager = ConversationManager()
        self.interactive_menu_service = InteractiveMenuService()
        self.chat_history_service = ChatHistoryService()
    
    def verify_webhook(self, request):
        """
        Verify webhook endpoint for WhatsApp Business API
        """
        # In production, implement proper verification with challenge parameter
        return "success"
    
    def handle_message(self, request) -> Dict[str, Any]:
        """
        Handle incoming WhatsApp messages
        """
        try:
            # Extract message data from Twilio webhook
            original_msg = request.values.get('Body', '').strip()
            from_number = request.values.get('From', '')
            num_media = int(request.values.get('NumMedia', 0))
            
            # Initialize response data
            response_data = {"status": "received", "message": "Message processed"}
            
            if num_media > 0:
                # Handle media messages (images, PDFs, videos)
                media_type = request.values.get('MediaContentType0', '').lower()
                media_url = request.values.get('MediaUrl0', '')
                
                # Process the media based on type
                if 'pdf' in media_type:
                    user_message = f"[PDF Analysis Request] Media URL: {media_url}"
                elif any(img_type in media_type for img_type in ['jpeg', 'png']):
                    user_message = f"[Image Analysis Request] Media URL: {media_url}"
                elif 'video' in media_type:
                    user_message = f"[Video Analysis Request] Media URL: {media_url}"
                else:
                    user_message = f"[Unsupported Media] Type: {media_type}"
                
                # Process through the graph
                result = self.graph.run(
                    user_input=user_message,
                    user_id=from_number,
                    initial_state={"user_input": user_message}
                )
                
                # Send response back to user
                self.send_whatsapp_message(result.get("messages", [])[-1].content if result.get("messages") else "Processed media successfully", from_number)
                
            elif original_msg:
                # Handle text messages
                # Detect language and translate if needed (but preserve numbers for menu selection)
                incoming_msg = original_msg if original_msg.isdigit() else self.translate_to_english(original_msg)
                
                # Check for menu selections first
                if self.process_menu_selection(incoming_msg, from_number):
                    return jsonify({"status": "menu_processed"})
                
                # Check if user wants the main menu (e.g., if they say 'menu', 'help', etc.)
                user_lower = original_msg.lower().strip()
                if any(word in user_lower for word in ['menu', 'help', 'options', 'main menu', 'start', 'hello']):
                    # Get user's name from history if available
                    user_history = self.chat_history_service.get_user_history(from_number)
                    user_name = self.extract_user_name(user_history)
                    menu_message = self.interactive_menu_service.get_main_menu(user_name or "there")
                    
                    # Translate menu if needed
                    if self.detect_language(original_msg) == 'or':
                        menu_message = self.translate_to_odia(menu_message)
                    
                    self.send_whatsapp_message(menu_message, from_number)
                    return jsonify({"status": "menu_sent"})
                
                # Process through the LangGraph workflow
                result = self.graph.run(
                    user_input=incoming_msg,
                    user_id=from_number
                )
                
                # Extract the response from the graph result
                if result.get("messages"):
                    bot_response = result["messages"][-1].content
                else:
                    bot_response = "Thank you for your message. How can I assist you with your health concerns today?"
                
                # Translate response back to user's language if needed
                if self.detect_language(original_msg) == 'or':
                    bot_response = self.translate_to_odia(bot_response)
                
                # Send response back to user
                self.send_whatsapp_message(bot_response, from_number)
            
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    def process_menu_selection(self, incoming_msg: str, from_number: str) -> bool:
        """
        Process menu selections from users
        """
        # Check if the message is a menu selection (1-5)
        if incoming_msg in [str(i) for i in range(1, 6)]:
            # Use the interactive menu service to process the selection
            response = self.interactive_menu_service.process_menu_selection(incoming_msg)
            
            if response:
                # Send response back to user
                self.send_whatsapp_message(response, from_number)
            
            return True
        
        return False
    
    def send_whatsapp_message(self, body: str, to_number: str, media_url: str = None):
        """
        Send a message via Twilio WhatsApp API
        """
        try:
            from twilio.rest import Client
            
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            # Split message if it's too long
            max_length = 1600
            if len(body) <= max_length:
                if media_url:
                    client.messages.create(
                        body=body,
                        from_=settings.TWILIO_WHATSAPP_NUMBER,
                        to=to_number,
                        media_url=[media_url] if media_url else None
                    )
                else:
                    client.messages.create(
                        body=body,
                        from_=settings.TWILIO_WHATSAPP_NUMBER,
                        to=to_number
                    )
            else:
                # Split long messages
                chunks = [body[i:i + max_length - 20] for i in range(0, len(body), max_length - 20)]
                for i, chunk in enumerate(chunks):
                    client.messages.create(
                        body=f"({i+1}/{len(chunks)})\n{chunk}",
                        from_=settings.TWILIO_WHATSAPP_NUMBER,
                        to=to_number
                    )
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
    
    def detect_language(self, text: str) -> str:
        """
        Simple language detection based on common Odia characters
        """
        # Check for common Odia Unicode ranges
        odia_chars = [char for char in text if '\u0B00' <= char <= '\u0B7F']
        if len(odia_chars) / len(text) > 0.1:  # If more than 10% of chars are Odia
            return 'or'
        return 'en'
    
    def extract_user_name(self, messages: list) -> str:
        """
        Extract user's name from conversation history
        """
        if not messages:
            return None
            
        for msg in messages:
            if isinstance(msg, dict) and msg.get('role') == 'user':
                text = msg['parts'][0].lower()
                if 'i am ' in text:
                    parts = text.split('i am ', 1)
                    if len(parts) > 1:
                        return parts[1].split()[0].capitalize()
                elif 'my name is ' in text:
                    parts = text.split('my name is ', 1)
                    if len(parts) > 1:
                        return parts[1].split()[0].capitalize()
                elif text.startswith('hello ') or text.startswith('hi '):
                    words = text.split()
                    if len(words) > 1:
                        return words[1].capitalize()
        return None
    
    def translate_to_english(self, text: str) -> str:
        """
        Translate Odia text to English
        """
        try:
            return GoogleTranslator(source='or', target='en').translate(text)
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text  # Return original text if translation fails
    
    def translate_to_odia(self, text: str) -> str:
        """
        Translate English text to Odia
        """
        try:
            return GoogleTranslator(source='en', target='or').translate(text)
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text  # Return original text if translation fails