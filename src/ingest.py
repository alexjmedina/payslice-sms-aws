import json, os
from utils.logger import log
from utils.twilio_client import build_client
from utils.secrets import get_twilio_secrets
from utils.idempotency import was_processed
import boto3

sqs = boto3.client("sqs")
QUEUE_URL = os.getenv("APPROVED_QUEUE_URL")
DELAY_SECONDS = int(os.getenv("APPROVED_DELAY_SECONDS", "120"))

client, conf = build_client()
SECRETS = get_twilio_secrets()

def _auth_ok(headers):
    auth = headers.get("authorization") or headers.get("Authorization")
    return (auth or "").split("Bearer ")[-1].strip() == SECRETS["bearer"]

def _send_now(to:str, body:str):
    return client.messages.create(
        to=to,
        messaging_service_sid=conf["msid"],
        body=body
    )

def lambda_handler(event, _ctx):
    if not _auth_ok(event.get("headers", {})):
        return {"statusCode": 401, "body": "unauthorized"}

    body = json.loads(event.get("body") or "{}")
    eid  = body.get("event_id")
    kind = body.get("event")
    phone = (body.get("user") or {}).get("phone")

    if not eid or not kind or not phone:
        return {"statusCode": 400, "body": "missing required fields"}

    # idempotency guard (optional)
    if was_processed(eid):
        return {"statusCode": 200, "body": "duplicate_ignored"}

    if kind == "advance_in_transit":
        res = _send_now(phone, "Ta-dah! Your advance is being sent! – PaySlice")
        log("sms.sent", type=kind, sid=res.sid, to=phone)
        return {"statusCode": 200, "body": json.dumps({"sid": res.sid})}

    if kind == "advance_approved":
        amount = body.get("amount")
        if amount is None:
            return {"statusCode": 400, "body": "amount required for advance_approved"}

        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps({"event_id": eid, "phone": phone, "amount": amount}),
            DelaySeconds=DELAY_SECONDS
        )
        log("queue.enqueued", type=kind, phone=phone, delay=DELAY_SECONDS)
        return {"statusCode": 202, "body": "queued"}

    return {"statusCode": 400, "body": "unsupported event"}
