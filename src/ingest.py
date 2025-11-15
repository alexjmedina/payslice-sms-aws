import json
import os

import boto3

from utils.logger import get_logger
from utils.twilio_client import build_client

log = get_logger("ingest")

sqs = boto3.client("sqs")
APPROVED_QUEUE_URL = os.environ["APPROVED_QUEUE_URL"]

twilio_client, twilio_conf = build_client()


def lambda_handler(event, context):
    raw_body = event.get("body") or "{}"
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        log("ingest.invalid_json", body_preview=raw_body[:200])
        return {"statusCode": 400, "body": '{"error":"invalid_json"}'}

    # Expect something like:
    # { "event": "advance_approved", "event_id": "...", "user": { "phone": ... }, "amount": 100.0, "send_in_transit_now": true }
    evt = payload.get("event")
    send_in_transit_now = bool(payload.get("send_in_transit_now"))

    # 1) Optional: send instant “in transit” SMS
    if send_in_transit_now:
        try:
            phone = payload["user"]["phone"]
            amount = payload["amount"]
            body = f"🎉 Your ${amount:.2f} advance is on its way! We’ve sent it to your bank. – PaySlice"
            resp = twilio_client.messages.create(
                messaging_service_sid=twilio_conf["messaging_service_sid"],
                to=phone,
                body=body,
            )
            log("ingest.twilio_in_transit_sent", sid=resp.sid, to=phone)
        except Exception as e:
            log("ingest.twilio_in_transit_error", error=str(e), payload=payload)
            # You can decide whether to still enqueue the delayed event or not.

    # 2) Always enqueue approved event for Worker
    msg_for_worker = {
        "event_id": payload.get("event_id"),
        "event": "advance_approved",
        "user": {"phone": payload["user"]["phone"]},
        "amount": payload["amount"],
    }

    resp = sqs.send_message(
        QueueUrl=APPROVED_QUEUE_URL,
        MessageBody=json.dumps(msg_for_worker),
        DelaySeconds=120,
    )
    log("ingest.enqueued", queue_url=APPROVED_QUEUE_URL, message_id=resp["MessageId"])

    return {"statusCode": 202, "body": '{"queued":true}'}
