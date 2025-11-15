import json
from typing import Any, Dict

from utils.logger import get_logger
from utils.twilio_client import build_client

log = get_logger("worker")

client, conf = build_client()


EVENT_TEMPLATES = {
    "advance_in_transit": lambda msg: (
        f"Ta-dah! Your advance of ${msg['amount']:.2f} is being sent!. 💸 – PaySlice"
    ),
    "advance_approved": lambda msg: (
        f"🎉 Your ${msg['amount']:.2f} advance has been approved. "
        "Funds are now moving to your bank. You’ll get another text once it lands. – Payslice."
    ),
}


def build_body(msg: Dict[str, Any]) -> str:
    event = msg.get("event")
    if event not in EVENT_TEMPLATES:
        raise ValueError(f"Unsupported event type: {event}")

    if "amount" not in msg:
        raise KeyError("amount")

    return EVENT_TEMPLATES[event](msg)


def lambda_handler(event, context):
    records = event.get("Records", [])
    for rec in records:
        raw_body = rec.get("body") or ""
        receipt_handle = rec.get("receiptHandle", "<no-handle>")

        try:
            msg = json.loads(raw_body)
        except json.JSONDecodeError:
            log(
                "worker.payload_invalid_json",
                body_preview=raw_body[:200],
                receipt_handle=receipt_handle,
            )
            # Let SQS redrive to DLQ after maxReceiveCount
            continue

        try:
            phone = msg["user"]["phone"]
        except KeyError:
            log(
                "worker.missing_phone",
                msg=msg,
                receipt_handle=receipt_handle,
            )
            continue

        try:
            body = build_body(msg)
        except Exception as e:
            log("worker.build_body_error", error=str(e), msg=msg)
            continue

        try:
            resp = client.messages.create(
                messaging_service_sid=conf["messaging_service_sid"],
                to=phone,
                body=body,
            )
            log(
                "worker.twilio_sent",
                sid=resp.sid,
                to=phone,
                event=msg.get("event"),
                event_id=msg.get("event_id"),
            )
        except Exception as e:
            log(
                "worker.twilio_error",
                error=str(e),
                to=phone,
                event=msg.get("event"),
            )
            # Again: let SQS retry and eventually DLQ
            continue
