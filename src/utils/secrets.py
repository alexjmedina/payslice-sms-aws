import os
import json

import boto3

from utils.logger import get_logger

logger = get_logger("secrets")


def _get_secret_name_and_region() -> tuple[str, str]:
    """
    Resolve the Twilio secret name and AWS region from environment variables.

    TWILIO_SECRET_NAME is required (you pass it via the TwilioSecretName parameter).
    AWS_REGION is optional; defaults to us-east-1 inside Lambda if not set.
    """
    secret_name = os.getenv("TWILIO_SECRET_NAME")
    region_name = os.getenv("AWS_REGION", "us-east-1")

    missing = []
    if not secret_name:
        missing.append("TWILIO_SECRET_NAME")

    if missing:
        msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(msg)
        raise RuntimeError(msg)

    return secret_name, region_name


def get_twilio_secrets() -> dict:
    """
    Fetch Twilio credentials/config from AWS Secrets Manager.

    Expects the secret value to be a JSON object, e.g.:

        {
          "account_sid": "...",
          "auth_token": "...",
          "msid": "..."
        }
    """
    secret_name, region_name = _get_secret_name_and_region()

    # Log using the Logger API, not as a callable
    logger.info(
        "Fetching Twilio secrets from Secrets Manager",
        extra={"secret_name": secret_name, "region": region_name},
    )

    # Ensure client is created for the correct region
    client = boto3.client("secretsmanager", region_name=region_name)

    resp = client.get_secret_value(SecretId=secret_name)
    secret_str = resp.get("SecretString")

    if not secret_str:
        msg = f"Secret '{secret_name}' has no SecretString payload"
        logger.error(msg)
        raise RuntimeError(msg)

    try:
        data = json.loads(secret_str)
    except json.JSONDecodeError as e:
        logger.error(
            "SecretString is not valid JSON",
            extra={"secret_name": secret_name, "error": str(e)},
        )
        raise

    # Optional: minimal validation
    # for field in ("account_sid", "auth_token", "msid"):
    #     if field not in data:
    #         logger.warning(
    #             "Twilio secret missing expected field",
    #             extra={"secret_name": secret_name, "field": field},
    #         )

    return data
