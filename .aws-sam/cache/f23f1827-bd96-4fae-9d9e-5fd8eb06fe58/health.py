import json, os

def lambda_handler(event, _ctx):
    path = event.get("rawPath", "/")
    if path.endswith("/version"):
        return {"statusCode":200,"body":json.dumps({"version": os.getenv("APP_VERSION","v1")})}
    return {"statusCode":200,"body":"ok"}
