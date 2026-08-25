import logging

from pyngrok import conf, ngrok

from config.settings import settings

logger = logging.getLogger(__name__)


def start_ngrok_tunnel() -> str | None:
    """Start ngrok tunnel and return the public HTTPS URL."""
    if settings.NGROK_AUTHTOKEN:
        conf.get_default().auth_token = settings.NGROK_AUTHTOKEN

    try:
        options: dict = {"addr": settings.PORT}
        if settings.NGROK_DOMAIN:
            options["domain"] = settings.NGROK_DOMAIN

        tunnel = ngrok.connect(**options)
        public_url = tunnel.public_url.replace("http://", "https://") if tunnel.public_url.startswith("http://") else tunnel.public_url
        logger.info("ngrok tunnel active: %s", public_url)
        logger.info("Webhook URL: %s/webhook", public_url)
        return public_url
    except Exception as exc:
        logger.warning("ngrok not started (%s). Run manually: ngrok http %s", exc, settings.PORT)
        return None
