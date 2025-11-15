import json
from urllib.parse import parse_qs

from utils.logger import get_logger

log = get_logger("twilio-status")


def lambda_handler(event, context):
    # Body from API Gateway HTTP API (v2)
    raw_body = event.get("body") or ""
    parsed = parse_qs(raw_body)

    # Flatten: {'MessageSid': ['SM...']} → {'MessageSid': 'SM...'}
    data = {k: v[0] for k, v in parsed.items() if v}

    # Optional: extract a few standard fields
    message_sid = data.get("MessageSid")
    message_status = data.get("MessageStatus") or data.get("SmsStatus")

    log(
        "twilio.status",
        message_sid=message_sid,
        message_status=message_status,
        raw=data,
    )

    # We don't block Twilio on internal errors; just acknowledge receipt.
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"ok": True}),
    }
