
def lambda_handler(event, context):
    print("Twilio Status:", event.get("body"))
    return {"statusCode": 200, "body": "ok"}
