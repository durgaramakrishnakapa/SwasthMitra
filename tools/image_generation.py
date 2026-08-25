import logging
import os
import time

import google.generativeai as genai
import requests
from langchain_core.tools import tool

from config.settings import settings

logger = logging.getLogger(__name__)
genai.configure(api_key=settings.GEMINI_API_KEY)
_model = genai.GenerativeModel(settings.GEMINI_MODEL)


def _public_base_url() -> str:
    try:
        resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=3)
        if resp.status_code == 200:
            for tunnel in resp.json().get("tunnels", []):
                if tunnel.get("proto") == "https":
                    return tunnel["public_url"].rstrip("/")
            tunnels = resp.json().get("tunnels", [])
            if tunnels:
                return tunnels[0]["public_url"].rstrip("/")
    except requests.RequestException:
        pass
    return f"http://localhost:{settings.PORT}"


@tool
def generate_health_image(prompt: str, user_id: str = "user") -> str:
    """Generate a health-related image (diet plate, exercise diagram, food chart, infographic).
    ONLY call when the user explicitly asks for a visual/image/diagram of health content."""
    if not settings.CLIPDROP_API_KEY:
        return "Image generation requires CLIPDROP_API_KEY. Please add it to your .env file."

    os.makedirs(settings.IMAGE_DIR, exist_ok=True)
    health_prompt = f"Clean medical health infographic, professional, educational: {prompt}"

    try:
        response = requests.post(
            "https://clipdrop-api.co/text-to-image/v1",
            files={"prompt": (None, health_prompt, "text/plain")},
            headers={"x-api-key": settings.CLIPDROP_API_KEY},
            timeout=90,
        )
        response.raise_for_status()

        safe_id = "".join(c for c in user_id if c.isalnum())[:20] or "user"
        filename = f"{safe_id}_{int(time.time())}.png"
        filepath = os.path.join(settings.IMAGE_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)

        image_url = f"{_public_base_url()}/generated/{filename}"

        caption_prompt = (
            f"Write a short WhatsApp caption (max 4 bullet points) for a health image about: {prompt}. "
            "Use • bullets, *bold* for key terms, 1-2 emojis."
        )
        caption = _model.generate_content(caption_prompt).text.strip()

        return f"IMAGE_URL:{image_url}\n\n{caption}"
    except Exception as exc:
        logger.error("Image generation failed: %s", exc)
        return f"Sorry, I couldn't generate the image: {exc}"
