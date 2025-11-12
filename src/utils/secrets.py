import json, os, base64
import boto3

SM_NAME = os.getenv("TWILIO_SECRET_NAME", "payslice/twilio/txn")

def _clean(s: str) -> str:
    # remove UTF-8 BOM + trim whitespace/newlines
    return s.lstrip("\ufeff").strip()

def get_twilio_secrets() -> dict:
    sm = boto3.client("secretsmanager")
    r = sm.get_secret_value(SecretId=SM_NAME)
    if "SecretString" in r:
        raw = _clean(r["SecretString"])
    else:
        raw = _clean(base64.b64encode(r["SecretBinary"]).decode("utf-8"))

    data = json.loads(raw)  # will raise clearly if malformed
    # validate required keys early
    for k in ("account_sid", "auth_token", "msid"):
        if not data.get(k):
            raise ValueError(f"Missing required secret key: {k}")
    return data
