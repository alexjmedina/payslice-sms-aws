import json, os, boto3
from utils.twilio_client import get_twilio_client
from utils.logger import log
from utils.secrets import get_secrets

sqs = boto3.client("sqs")
def lambda_handler(event, context):
    secrets = get_secrets()
    auth = (event.get("headers") or {}).get("authorization", "")
    if auth != f"Bearer {secrets['INTERNAL_BEARER_TOKEN']}":
        return {"statusCode": 403, "body": "Forbidden"}

    body = json.loads(event.get("body") or "{}")
    evt = body.get("event")
    phone = body.get("phone")
    amount = body.get("amount", "")
    if not evt or not phone:
        return {"statusCode": 400, "body": "Missing fields"}

    client, cfg = get_twilio_client()

    if evt == "advance_in_transit":
        msg = client.messages.create(
            to=phone,
            messaging_service_sid=cfg["TWILIO_MSID"],
            body="Ta-dah! Your advance is being sent! 💸 – Payslice"
        )
        log("sent_in_transit", phone=phone, sid=msg.sid)
        return {"statusCode": 200, "body": json.dumps({"sid": msg.sid})}

    if evt == "advance_approved":
        queue_url = os.environ["APPROVED_QUEUE_URL"]
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps({"phone": phone, "amount": amount}))
        log("queued_approved", phone=phone)
        return {"statusCode": 202, "body": json.dumps({"scheduled": 120})}

    return {"statusCode": 400, "body": "Unknown event"}
