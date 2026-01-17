import google.generativeai as genai
from config.settings import settings
import json
import logging

logger = logging.getLogger(__name__)

class MedicalAdvisor:
    """
    Provides medical advice based on symptoms using AI
    """
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-pro")
    
    def get_medical_advice(self, symptoms: str, conversation_history: list = None) -> str:
        """
        Generate medical advice based on symptoms and conversation history
        """
        try:
            # Prepare conversation history context
            history_context = ""
            if conversation_history:
                recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
                history_context = " ".join([msg['parts'][0] if isinstance(msg, dict) and 'parts' in msg else str(msg) 
                                          for msg in recent_history])
            
            # Create prompt for medical advice
            prompt = f"""
            You are a friendly medical assistant. Provide helpful medical advice based on the user's symptoms.
            Be cautious and remind the user that this is not a substitute for professional medical advice.
            
            Symptoms/Concerns: {symptoms}
            
            Conversation History (if any): {history_context}
            
            Please format your response for WhatsApp with:
            - Brief, clear advice
            - Use *bold* for important medical terms
            - Add relevant emojis (like 🩺, 💡, 🩹, 🏥)
            - Use bullet points when listing items
            - Keep line length reasonable for mobile screens
            - Include a reminder that this is for informational purposes only
            - Suggest consulting a doctor if symptoms persist or worsen
            
            Be empathetic and supportive while maintaining medical accuracy.
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating medical advice: {e}")
            return (
                "I'm sorry, I had trouble generating medical advice at the moment. "
                "Please consult with a healthcare professional for your concerns. 🏥\n\n"
                "Remember, this service is for informational purposes only and not a substitute for professional medical advice. 💡"
            )
    
    def extract_symptoms(self, user_input: str) -> str:
        """
        Extract symptoms from user input
        """
        try:
            prompt = f"""
            Extract the main symptoms or health concerns from the following text:
            "{user_input}"
            
            Return only the symptoms separated by commas. If no clear symptoms are mentioned, return "general health inquiry".
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting symptoms: {e}")
            return "general health inquiry"