import json
from urllib.parse import parse_qs

from utils.logger import log


def lambda_handler(event, _ctx):
    """
    Twilio status webhooks are sent as application/x-www-form-urlencoded.

    Example body:
      MessageSid=SM123&MessageStatus=sent&To=%2B1305...

    API Gateway (HTTP API) forwards that as a raw string in event["body"].
    We parse it into a clean dict and log it.
    """
    body_str = event.get("body") or ""

    # Parse form-encoded string -> dict of lists
    parsed = parse_qs(body_str)
    # Flatten one-element lists so logs are readable: {"MessageSid": "SM...", ...}
    payload = {
        key: (values[0] if isinstance(values, list) and values else values)
        for key, values in parsed.items()
    }

    # Log structured event for observability
    log("twilio.status", **payload)

    # Respond 200 so Twilio knows the webhook succeeded
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"ok": True}),
    }
