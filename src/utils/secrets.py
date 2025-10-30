import os, json, boto3

def get_twilio_secrets(secret_name=None, region=None):
    name   = secret_name or os.getenv("TWILIO_SECRET_NAME", "payslice/twilio/txn")
    region = region or os.getenv("AWS_REGION", "us-east-1")
    sm = boto3.client("secretsmanager", region_name=region)
    s = sm.get_secret_value(SecretId=name)
    raw = s.get("SecretString") or s["SecretBinary"].decode()
    data = json.loads(raw)
    return {
        "account_sid": data["TWILIO_ACCOUNT_SID"],
        "auth_token":  data["TWILIO_AUTH_TOKEN"],
        "msid":        data.get("TWILIO_MESSAGING_SERVICE_SID") or data["TWILIO_MSID"],
        "bearer":      data.get("INTERNAL_BEARER") or data["INTERNAL_BEARER_TOKEN"],
    }
