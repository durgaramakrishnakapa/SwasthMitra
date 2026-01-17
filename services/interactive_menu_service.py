from typing import Dict, List, Optional
from config.settings import settings
from deep_translator import GoogleTranslator
import logging

logger = logging.getLogger(__name__)

class InteractiveMenuService:
    """
    Service for handling interactive health menus and options
    """
    
    def __init__(self):
        self.menu_options = {
            "1": "🏥 Find Hospitals Near Me",
            "2": "💊 Symptom Checker", 
            "3": "📅 Book Appointment",
            "4": "🆘 Emergency",
            "5": "📊 Health Tips"
        }
    
    def get_main_menu(self, user_name: str = "there") -> str:
        """
        Generate the main interactive health menu
        """
        menu_message = f"Hello {user_name}! 👋 How can Swasth Mitra assist you today?\n\nPlease select an option:"
        
        for key, option in self.menu_options.items():
            menu_message += f"\n{key}. {option}"
        
        menu_message += "\n\nReply with the number or type your own health concern."
        
        return menu_message
    
    def process_menu_selection(self, selection: str, user_name: str = "there") -> Optional[str]:
        """
        Process a menu selection and return an appropriate response
        """
        selection = selection.strip().lower()
        
        # Map numeric selections to actions
        selection_actions = {
            "1": "Please share your location (city or area) to find nearby hospitals.",
            "2": "Please describe your symptoms briefly.",
            "3": "Please share which specialist you'd like to book an appointment with.",
            "4": "Emergency services have been alerted. Help is on the way.",
            "5": "Here are some general health tips:\n• Stay hydrated 💧\n• Get 7-8 hours of sleep 😴\n• Eat a balanced diet 🥗\n• Exercise regularly 🏃‍♀️"
        }
        
        if selection in selection_actions:
            return selection_actions[selection]
        
        # Check if it's a keyword-based selection
        if any("hospital" in selection or "clinic" in selection):
            return "Please share your location (city or area) to find nearby hospitals."
        elif any(word in selection for word in ["symptom", "check", "problem", "issue"]):
            return "Please describe your symptoms briefly."
        elif any(word in selection for word in ["book", "appoint", "schedule"]):
            return "Please share which specialist you'd like to book an appointment with."
        elif any(word in selection for word in ["emerg", "urgent", "help"]):
            return "Emergency services have been alerted. Help is on the way."
        elif any(word in selection for word in ["tip", "health", "advice"]):
            return "Here are some general health tips:\n• Stay hydrated 💧\n• Get 7-8 hours of sleep 😴\n• Eat a balanced diet 🥗\n• Exercise regularly 🏃‍♀️"
        
        return None
    
    def send_interactive_health_menu(self, to_number: str, user_name: str = "there"):
        """
        Send the interactive health menu to a user (would integrate with WhatsApp service)
        """
        menu_message = self.get_main_menu(user_name)
        
        # This would typically call the WhatsApp messaging service
        # For now, we return the message for the calling function to handle
        return menu_message
    
    def detect_language(self, text: str) -> str:
        """
        Simple language detection based on common Odia characters
        """
        # Check for common Odia Unicode ranges
        odia_chars = [char for char in text if '\u0B00' <= char <= '\u0B7F']
        if len(odia_chars) / len(text) > 0.1:  # If more than 10% of chars are Odia
            return 'or'
        return 'en'
    
    def translate_to_odia(self, text: str) -> str:
        """
        Translate English text to Odia
        """
        try:
            return GoogleTranslator(source='en', target='or').translate(text)
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text  # Return original text if translation fails
    
    def translate_to_english(self, text: str) -> str:
        """
        Translate Odia text to English
        """
        try:
            return GoogleTranslator(source='or', target='en').translate(text)
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text  # Return original text if translation fails