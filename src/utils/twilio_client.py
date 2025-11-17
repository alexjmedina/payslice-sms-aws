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
          - conf: dict with at least {"msid": "..."}
    """
    secrets = get_twilio_secrets()

    # Support both dict-style and attribute-style secrets
    if isinstance(secrets, dict):
        account_sid = secrets.get("account_sid")
        auth_token = secrets.get("auth_token")
        msid = secrets.get("msid")
    else:
        account_sid = getattr(secrets, "account_sid", None)
        auth_token = getattr(secrets, "auth_token", None)
        msid = getattr(secrets, "msid", None)

    missing = [
        name
        for name, value in [
            ("account_sid", account_sid),
            ("auth_token", auth_token),
            ("msid", msid),
        ]
        if not value
    ]

    if missing:
        logger.error(
            "Missing Twilio secrets",
            extra={"missing": missing},
        )
        raise RuntimeError(f"Missing Twilio secrets: {', '.join(missing)}")

    client = TwilioClient(account_sid, auth_token)
    logger.info("Twilio client initialized successfully")

    conf = {"msid": msid}
    return client, conf
