import json
from utils.twilio_client import get_twilio_client
from utils.logger import log

client, cfg = get_twilio_client()

def lambda_handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        msg = client.messages.create(
            to=body["phone"],
            messaging_service_sid=cfg["TWILIO_MSID"],
            body=f"🎉 Your {body.get('amount','')} advance was approved! Funds are now moving to your bank. You’ll get another text once it lands. – Payslice"
        )
        log("sent_approved", phone=body["phone"], sid=msg.sid)
    return {"statusCode": 200}
