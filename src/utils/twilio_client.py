# utils/twilio_client.py

from twilio.rest import Client as TwilioClient

from utils.logger import get_logger
from utils.secrets import get_twilio_secrets

logger = get_logger("twilio_client")


def build_client():
    """
    Build and return a Twilio client plus a small config dict.

    Returns:
        (client, conf) where:
          - client: twilio.rest.Client
          - conf: dict with at least {"messaging_service_sid": "..."}
    """
    secrets = get_twilio_secrets()

    # Secrets are expected to be a dict like:
    # {
    #   "account_sid": "...",
    #   "auth_token": "...",
    #   "msid": "MGxxx",   # legacy name
    #   "bearer": "..."    # optional
    # }
    # or possibly with "messaging_service_sid" instead of "msid".
    if isinstance(secrets, dict):
        account_sid = secrets.get("account_sid")
        auth_token = secrets.get("auth_token")

        # Support both "messaging_service_sid" and legacy "msid"
        messaging_service_sid = (
            secrets.get("messaging_service_sid") or secrets.get("msid")
        )

        bearer_token = secrets.get("bearer")  # optional, for future use
    else:
        # Attribute-style fallback (not expected with your current JSON)
        account_sid = getattr(secrets, "account_sid", None)
        auth_token = getattr(secrets, "auth_token", None)
        messaging_service_sid = (
            getattr(secrets, "messaging_service_sid", None)
            or getattr(secrets, "msid", None)
        )
        bearer_token = getattr(secrets, "bearer", None)

    missing = [
        name
        for name, value in [
            ("account_sid", account_sid),
            ("auth_token", auth_token),
            ("messaging_service_sid", messaging_service_sid),
        ]
        if not value
    ]

    if missing:
        logger.error("Missing Twilio secrets", extra={"missing": missing})
        raise RuntimeError(f"Missing Twilio secrets: {', '.join(missing)}")

    client = TwilioClient(account_sid, auth_token)
    logger.info("Twilio client initialized successfully")

    conf = {
        "messaging_service_sid": messaging_service_sid,
        # keep bearer in case we want it later for other APIs
        "bearer": bearer_token,
    }

    return client, conf
