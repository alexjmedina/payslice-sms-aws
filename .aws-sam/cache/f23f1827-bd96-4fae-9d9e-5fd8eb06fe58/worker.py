import json
from utils.logger import log
from utils.twilio_client import build_client

client, conf = build_client()

def lambda_handler(event, _ctx):
    for rec in event["Records"]:
        msg = json.loads(rec["body"])
        body = f"🎉 Your ${msg['amount']:.2f} advance was approved! Funds are moving to your bank. – PaySlice"
        res = client.messages.create(
            to=msg["phone"],
            messaging_service_sid=conf["msid"],
            body=body
        )
        log("sms.sent", type="advance_approved", sid=res.sid, to=msg["phone"])
    return {"statusCode": 200}
