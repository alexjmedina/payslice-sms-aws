import os
import json
import boto3
from aws_lambda_powertools import Logger

logger = Logger(service="twilio-secrets")

_sm = boto3.client("secretsmanager")


def _clean(s: str) -> str:
    """
    Normalize SecretString so it's valid JSON:
    - strip whitespace
    - remove BOM variants (UTF-8 ï»¿ or \ufeff)
    - drop any junk before the first '{'
    """
    if not isinstance(s, str):
        return s

    # Trim outer whitespace/newlines first
    s = s.strip()

    # Case 1: normal BOM codepoint
    if s.startswith("\ufeff"):
        s = s.lstrip("\ufeff").strip()

    # Case 2: BOM got stored as literal UTF-8 bytes: \u00ef\u00bb\u00bf  (ï»¿)
    # Powertools showed exactly this in the logs.
    if s.startswith("\u00ef\u00bb\u00bf"):
        s = s[len("\u00ef\u00bb\u00bf"):].strip()

    # Final safety net: find the first '{' and drop anything before it
    brace_idx = s.find("{")
    if brace_idx > 0:
        s = s[brace_idx:]

    return s



def get_twilio_secrets() -> dict:
    """
    Load and parse the Twilio secrets JSON from AWS Secrets Manager.
    Fails loudly (with clear logs) if anything is wrong.
    """
    name = os.getenv("TWILIO_SECRET_NAME")
    if not name:
        # Fatal misconfiguration – no env var
        logger.error("TWILIO_SECRET_NAME env var is missing")
        raise RuntimeError("TWILIO_SECRET_NAME env var is not set")

    logger.info(f"Fetching Twilio secrets from Secrets Manager: {name}")

    resp = _sm.get_secret_value(SecretId=name)

    raw = resp.get("SecretString", "")
    logger.info(f"Raw SecretString length before cleaning: {len(raw)}")

    cleaned = _clean(raw)
    logger.info(f"SecretString length after cleaning: {len(cleaned)}")

    if not cleaned:
        # This is the situation we’re seeing right now
        logger.error(
            f"Secret {name!r} is empty after cleaning. "
            "Check its value in AWS Secrets Manager (SecretString)."
        )
        raise RuntimeError(
            f"Secret {name!r} is empty or missing SecretString; "
            "cannot initialize Twilio client."
        )

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.exception(
            f"Failed to parse Twilio secret JSON for {name!r}: {e}. "
            f"First 100 chars: {cleaned[:100]!r}"
        )
        raise

    # Optional: sanity-check keys
    for key in ("account_sid", "auth_token", "msid"):
        if key not in data:
            logger.warning(f"Twilio secret is missing key {key!r}")

    logger.info("Twilio secrets loaded successfully")
    return data
