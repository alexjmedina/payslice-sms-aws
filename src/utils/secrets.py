import json
import os
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from utils.logger import get_logger

log = get_logger("twilio-secrets")


@dataclass(frozen=True)
class TwilioSecrets:
    account_sid: str
    auth_token: str
    msid: str
    bearer: str


def get_twilio_secrets() -> TwilioSecrets:
    secret_name = os.environ.get("TWILIO_SECRET_NAME", "payslice/twilio/txn")
    region_name = os.environ.get("AWS_REGION", "us-east-1")

    log("twilio.secrets.fetch", secret_name=secret_name, region=region_name)

    client = boto3.client("secretsmanager", region_name=region_name)

    try:
        resp = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        log("twilio.secrets.error", error=str(e))
        raise

    raw = resp.get("SecretString") or ""
    # Keep a minimal guard for BOM just in case:
    cleaned = raw.lstrip("\ufeff").strip()

    data = json.loads(cleaned)

    for field in ("account_sid", "auth_token", "msid", "bearer"):
        if field not in data:
            raise ValueError(f"Missing '{field}' in Twilio secret '{secret_name}'")

    log("twilio.secrets.loaded")

    return TwilioSecrets(
        account_sid=data["account_sid"],
        auth_token=data["auth_token"],
        msid=data["msid"],
        bearer=data["bearer"],
    )
