from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Dict, Any
import twilio
from twilio.rest import Client
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class EmergencyContactInput(BaseModel):
    summary: str = Field(description="Summary of the emergency situation")
    user_id: str = Field(description="User ID who triggered the emergency")
    emergency_contact: str = Field(description="Emergency contact number")
    conversation_history: list = Field(description="Conversation history for context")


class EmergencyContactTool(BaseTool):
    name = "emergency_contact_tool"
    description = "Trigger emergency alerts to notify emergency contacts"
    args_schema: Type[BaseModel] = EmergencyContactInput

    def __init__(self):
        super().__init__()
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.twilio_voice_number = settings.TWILIO_VOICE_NUMBER
        self.whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER

    def _summarize_conversation(self, history: list) -> str:
        """Summarize the recent conversation to include in emergency alerts."""
        if not history:
            return "No recent conversation history available."
        
        # Get the last few messages for context
        recent_messages = history[-6:] if len(history) > 6 else history
        
        # Separate user and bot messages
        user_messages = [msg for msg in recent_messages if msg['role'] == 'user']
        bot_responses = [msg for msg in recent_messages if msg['role'] == 'model']
        
        # Extract key information
        summary_parts = []
        
        if user_messages:
            summary_parts.append("Recent concerns:")
            for i, msg in enumerate(user_messages[-3:], 1):  # Last 3 user messages
                summary_parts.append(f"  {i}. {msg['parts'][0]}")
        
        return "\n".join(summary_parts)

    def _make_emergency_voice_call(self, message_text: str, recipient_number: str):
        """Makes a voice call and reads an emergency message."""
        twiml = f"<Response><Say voice='Polly.Aditi' language='en-IN'>{message_text}</Say></Response>"
        try:
            print(f"Initiating emergency call to {recipient_number}...")
            call = self.client.calls.create(twiml=twiml, to=recipient_number, from_=self.twilio_voice_number)
            print(f"Call initiated with SID: {call.sid}")
        except Exception as e:
            print(f"Error making call: {e}")

    def _send_emergency_sms(self, message_text: str, recipient_number: str):
        """Sends an emergency SMS."""
        try:
            print(f"Sending emergency SMS to {recipient_number}...")
            message = self.client.messages.create(
                body=message_text, 
                from_=self.twilio_voice_number, 
                to=recipient_number
            )
            print(f"SMS sent with SID: {message.sid}")
        except Exception as e:
            print(f"Error sending SMS: {e}")

    def _run(self, summary: str, user_id: str, emergency_contact: str, conversation_history: list = None) -> str:
        """Execute the emergency contact tool."""
        # Create conversation summary if history is provided
        conversation_summary = ""
        if conversation_history:
            conversation_summary = self._summarize_conversation(conversation_history)
        
        # Enhanced messages with conversation summary
        call_msg = f"🚨 EMERGENCY ALERT from Swasth Mitra Health Assistant 🚨\nUser: {user_id}\nSituation: {summary}\n\nConversation Summary:\n{conversation_summary}\n\nPlease respond immediately and contact emergency services if needed."
        
        sms_msg = f"🚨 EMERGENCY ALERT from Swasth Mitra 🚨\nUser: {user_id}\nSituation: {summary}\n\nConversation Summary:\n{conversation_summary}\n\nPlease call the user immediately and seek medical help if needed."
        
        self._make_emergency_voice_call(call_msg, emergency_contact)
        self._send_emergency_sms(sms_msg, emergency_contact)
        
        logger.info("Emergency alerts sent to contact with conversation summary.")
        return "🚨 Emergency services have been notified. Help is on the way. Please stay calm and follow any instructions from emergency services."
    
    def run(self, inputs: Dict[str, Any]) -> str:
        """Run the tool with the given inputs."""
        return self._run(
            summary=inputs.get("summary", ""),
            user_id=inputs.get("user_id", ""),
            emergency_contact=inputs.get("emergency_contact", ""),
            conversation_history=inputs.get("conversation_history", [])
        )