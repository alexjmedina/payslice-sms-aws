from utils.logger import get_logger

log = get_logger("health")


def lambda_handler(event, context):
    log("health.check", path="/health", method=event.get("requestContext", {}).get("http", {}).get("method", "GET"))
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"status":"ok"}',
    }
