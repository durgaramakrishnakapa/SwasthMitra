import logging

from langchain_core.tools import tool

from config.settings import settings

logger = logging.getLogger(__name__)


def _summarize_history(history: list) -> str:
    if not history:
        return "No recent conversation."
    lines = []
    for entry in history[-6:]:
        role = entry.get("role", "user")
        content = entry.get("content") or entry.get("parts", [""])[0]
        lines.append(f"{role}: {content[:100]}")
    return "\n".join(lines)


@tool
def trigger_emergency_alert(reason: str, user_id: str = "unknown") -> str:
    """Trigger emergency voice call and SMS to the user's emergency contact.
    ONLY use for genuine medical emergencies: chest pain, stroke, severe bleeding,
    difficulty breathing, unconsciousness, or life-threatening situations."""
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Emergency triggered but Twilio not configured. Reason: %s", reason)
        return (
            "🚨 Emergency noted. Twilio is not configured yet — please call 108/102 "
            "or your nearest hospital immediately. Stay calm."
        )

    contact = settings.EMERGENCY_CONTACT_NUMBER
    if not contact:
        return "🚨 Emergency noted. No emergency contact configured. Please call 108 immediately."

    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        alert = (
            f"🚨 EMERGENCY from Swasth Mitra\nUser: {user_id}\nReason: {reason}\n"
            "Please contact the user immediately."
        )

        if settings.TWILIO_VOICE_NUMBER:
            twiml = f"<Response><Say voice='Polly.Aditi' language='en-IN'>{alert}</Say></Response>"
            client.calls.create(twiml=twiml, to=contact, from_=settings.TWILIO_VOICE_NUMBER)
            client.messages.create(body=alert, from_=settings.TWILIO_VOICE_NUMBER, to=contact)

        logger.info("Emergency alert sent for user %s", user_id)
        return (
            "🚨 Emergency alert sent to your emergency contact. "
            "Help is on the way. Stay calm and follow emergency service instructions."
        )
    except Exception as exc:
        logger.error("Emergency alert failed: %s", exc)
        return f"🚨 Could not reach emergency contact ({exc}). Please call 108/102 immediately."
