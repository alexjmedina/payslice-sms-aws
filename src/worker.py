import json
from typing import Any, Dict

from utils.logger import get_logger
from utils.twilio_client import build_client

logger = get_logger("worker")

# Twilio client + config (from Secrets Manager)
client, conf = build_client()

# Supported SMS templates by event type
EVENT_TEMPLATES = {
    "advance_in_transit": lambda msg: (
        f"Ta-dah! Your advance of ${msg['amount']:.2f} is being sent!. 💸 – PaySlice"
    ),
    "advance_approved": lambda msg: (
        f"🎉 Your ${msg['amount']:.2f} advance has been approved. "
        "Funds are now moving to your bank. You’ll get another text once it lands. – PaySlice."
    ),
}


def build_body(msg: Dict[str, Any]) -> str:
    """
    Build the SMS body based on the event type and payload.
    """
    event = msg.get("event")
    if event not in EVENT_TEMPLATES:
        raise ValueError(f"Unsupported event type: {event}")

    if "amount" not in msg:
        raise KeyError("amount")

    return EVENT_TEMPLATES[event](msg)


def lambda_handler(event, context):
    records = event.get("Records", [])
    logger.info("worker.lambda_start: received %d records", len(records))

    for rec in records:
        raw_body = rec.get("body") or ""
        receipt_handle = rec.get("receiptHandle", "<no-handle>")

        # 1) Parse JSON from SQS
        try:
            msg = json.loads(raw_body)
        except json.JSONDecodeError:
            logger.warning(
                "worker.payload_invalid_json: preview=%s receipt_handle=%s",
                raw_body[:200],
                receipt_handle,
            )
            # Let SQS redrive to DLQ after maxReceiveCount
            continue

        # 2) Extract phone
        try:
            phone = msg["user"]["phone"]
        except KeyError:
            logger.warning(
                "worker.missing_phone: msg=%s receipt_handle=%s",
                msg,
                receipt_handle,
            )
            continue

        # 3) Build SMS body
        try:
            body = build_body(msg)
        except Exception as e:
            logger.error(
                "worker.build_body_error: error=%s msg=%s",
                str(e),
                msg,
            )
            continue

        # 4) Send via Twilio
        try:
            resp = client.messages.create(
                # IMPORTANT: Twilio expects "messaging_service_sid", not "msid"
                messaging_service_sid=conf["messaging_service_sid"],
                to=phone,
                body=body,
            )
            logger.info(
                "worker.twilio_sent: sid=%s to=%s event=%s event_id=%s",
                getattr(resp, "sid", "<no-sid>"),
                phone,
                msg.get("event"),
                msg.get("event_id"),
            )
        except Exception as e:
            logger.error(
                "worker.twilio_error: error=%s to=%s event=%s",
                str(e),
                phone,
                msg.get("event"),
            )
            # Let SQS retry and eventually DLQ
            continue
