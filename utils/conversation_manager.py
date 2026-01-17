from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import google.generativeai as genai
from config.settings import settings
from deep_translator import GoogleTranslator
import json
import logging

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Manages conversation flow and context
    """
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-pro")
    
    def process_conversation(self, user_input: str, messages: list) -> str:
        """
        Process user input in the context of the conversation
        """
        try:
            # Detect if input is in Odia and translate to English for processing
            detected_language = self.detect_language(user_input)
            original_input = user_input
            
            if detected_language == 'or':  # Odia
                user_input = self.translate_to_english(user_input)
            
            # Check if user is asking for their name
            if any(phrase in user_input.lower() for phrase in ["what is my name", "do you know my name", "what's my name"]):
                user_name = self.extract_user_name(messages)
                if user_name:
                    response = f"Of course! Your name is {user_name}. 😊\n\nHow can I help with your health concerns today? 🩺"
                else:
                    response = "I don't recall your name. How can I assist you with your health today? 💡"
                
                # Translate back to Odia if original was in Odia
                if detected_language == 'or':
                    response = self.translate_to_odia(response)
                
                return response
            
            # Check for affirmative responses
            if user_input.lower().strip() in ["yes", "yes please", "sure", "okay", "ok"] and messages:
                last_bot_message = ""
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        last_bot_message = msg.content
                        break
                
                if any(phrase in last_bot_message.lower() for phrase in ["call", "parents", "emergency"]):
                    response = "I've dispatched an emergency alert to your parents. Help is on the way. 🚨"
                elif any(phrase in last_bot_message.lower() for phrase in ["image", "picture", "diagram", "visual", "diet", "precaution"]):
                    response = "I can help create a visual for you. Could you please specify what kind of image you'd like? 🖼️"
                elif any(phrase in last_bot_message.lower() for phrase in ["upload", "report", "pdf", "document"]):
                    response = "Please upload any medical reports or documents you'd like me to analyze. 📄"
                else:
                    response = self.continue_conversation(user_input, messages)
            else:
                response = self.continue_conversation(user_input, messages)
            
            # Translate response back to Odia if original input was in Odia
            if detected_language == 'or':
                response = self.translate_to_odia(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing conversation: {e}")
            error_response = "I'm sorry, I had trouble processing your message. Could you please rephrase or try again? 💬"
            
            # Translate error response if needed
            if detected_language == 'or':
                error_response = self.translate_to_odia(error_response)
            
            return error_response
    
    def continue_conversation(self, user_input: str, messages: list) -> str:
        """
        Continue the conversation based on the user input and message history
        """
        try:
            # Format messages for context
            formatted_history = []
            for msg in messages[-6:]:  # Use last 6 messages for context
                if isinstance(msg, HumanMessage):
                    formatted_history.append({"role": "user", "parts": [msg.content]})
                elif isinstance(msg, AIMessage):
                    formatted_history.append({"role": "model", "parts": [msg.content]})
            
            # Check if the last message was a question to maintain conversation flow
            last_msg_is_question = False
            if messages:
                last_msg = messages[-1]
                if isinstance(last_msg, AIMessage) and last_msg.content.strip().endswith('?'):
                    last_msg_is_question = True
            
            if last_msg_is_question:
                question_count = 0
                for msg in reversed(messages[-6:]):
                    if isinstance(msg, AIMessage) and msg.content.strip().endswith('?'):
                        question_count += 1
                
                if question_count >= 2:
                    # If there are multiple questions, try to form a hypothesis
                    hypothesis_prompt = f"Based on this conversation, what is the most likely condition? Conversation: {json.dumps(formatted_history)} User's latest response: '{user_input}' Respond with ONLY the condition name."
                    try:
                        hypothesis_response = self.model.generate_content(hypothesis_prompt)
                        likely_condition = hypothesis_response.text.strip()
                        prompt = f"You are 'Swasth Mitra', a compassionate AI doctor. Based on the conversation, the user may have *{likely_condition}*. Ask ONE specific follow-up question to confirm or refine this hypothesis. After your question, offer: \"Would you like me to create an image with helpful information about this?\" Conversation History: {json.dumps(formatted_history)} User's latest answer: '{user_input}'"
                    except Exception:
                        prompt = f"You are 'Swasth Mitra', a compassionate AI doctor. Ask ONE specific follow-up question to better understand the user's condition. Keep it focused and relevant. Conversation History: {json.dumps(formatted_history)} User's latest answer: '{user_input}' After your question, offer: \"Would you like me to create an image with helpful information about this?\""
                else:
                    prompt = f"You are 'Swasth Mitra', a compassionate AI doctor. Ask ONE specific follow-up question to better understand the user's condition. Keep it focused and relevant. Conversation History: {json.dumps(formatted_history)} User's latest answer: '{user_input}' After your question, offer: \"Would you like me to create an image with helpful information about this?\""
            else:
                # Extract user name from history
                user_name = self.extract_user_name(messages)
                name_context = f" {user_name}" if user_name else ""
                prompt = f"You are 'Swasth Mitra', a compassionate AI doctor. The user{name_context} has a new health concern. Ask ONE specific question to understand their main symptom or concern. Do NOT greet them again. User's message: '{user_input}' After your question, offer: \"Would you like me to create an image with helpful information about this?\""
            
            # Generate response using the model
            chat = self.model.start_chat(history=formatted_history)
            raw_response = chat.send_message(prompt).text
            
            # Format the response for WhatsApp
            formatted_response = self.format_response_for_whatsapp(raw_response)
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error continuing conversation: {e}")
            return "I'm sorry, I had trouble processing your message. Could you please rephrase or try again? 💬"
    
    def extract_user_name(self, messages: list) -> str:
        """
        Extract user's name from conversation history
        """
        for msg in messages:
            if isinstance(msg, HumanMessage):
                text = msg.content.lower()
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
    
    def detect_language(self, text: str) -> str:
        """
        Simple language detection based on common Odia characters
        """
        # Check for common Odia Unicode ranges
        odia_chars = [char for char in text if '\u0B00' <= char <= '\u0B7F']
        if len(odia_chars) / len(text) > 0.1:  # If more than 10% of chars are Odia
            return 'or'
        return 'en'
    
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
    
    def format_response_for_whatsapp(self, raw_text: str) -> str:
        """
        Format the response to be professional, concise, and easy to read on WhatsApp
        """
        try:
            prompt = f"""
            You are a friendly medical assistant. Reformat the following text to be professional, concise, and easy to read on WhatsApp.
            Formatting requirements:
            - Keep responses brief and to the point (under 5 short paragraphs)
            - Use *bold text* ONLY for the most important medical terms, findings, or recommendations
            - Add relevant emojis (like 🩺, 💡, 🩹, 🏥) sparingly to enhance readability
            - Use bullet points when listing items
            - Keep line length reasonable for mobile screens
            - Remove unnecessary formatting and excessive stars
            Text to format: '{raw_text}'
            """
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Formatting error: {e}")
            return raw_text