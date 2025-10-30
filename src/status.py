import json
from utils.logger import log

def lambda_handler(event, _ctx):
    body = json.loads(event.get("body") or "{}")
    log("twilio.status", **body)
    return {"statusCode": 200}
