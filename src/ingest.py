import json
import os
from typing import Tuple

import boto3

from utils.logger import get_logger
from utils.twilio_client import build_client

logger = get_logger("ingest")

# Reuse AWS clients across invocations
sqs = boto3.client("sqs")

# Build Twilio client once per container
twilio_client, twilio_conf = build_client()


def _load_env() -> Tuple[str, int, str]:
    """
    Load required environment variables for the ingest function.

    APPROVED_QUEUE_URL: SQS queue URL for approved events
    APPROVED_DELAY_SECONDS: Delay (in seconds) before Worker processes message
    IDEMPOTENCY_TABLE: DynamoDB table name (reserved for future use here;
                       actively used by the Worker microservice)

    Raises RuntimeError with a clear message if something is missing/invalid.
    """
    approved_queue_url = os.getenv("APPROVED_QUEUE_URL")
    idempotency_table = os.getenv("IDEMPOTENCY_TABLE")
    approved_delay_str = os.getenv("APPROVED_DELAY_SECONDS", "120")

    missing = []
    if not approved_queue_url:
        missing.append("APPROVED_QUEUE_URL")
    if not idempotency_table:
        # We still validate it because the stack sets it,
        # and Worker relies on the same table.
        missing.append("IDEMPOTENCY_TABLE")

    if missing:
        msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(msg)
        raise RuntimeError(msg)

    try:
        approved_delay_seconds = int(approved_delay_str)
    except ValueError:
        msg = (
            f"Invalid APPROVED_DELAY_SECONDS='{approved_delay_str}'. "
            "Must be an integer number of seconds."
        )
        logger.error(msg)
        raise RuntimeError(msg)

    return approved_queue_url, approved_delay_seconds, idempotency_table


def _parse_body(event: dict) -> dict:
    """
    Extract and parse the JSON body from the Lambda event.

    - For API Gateway / HttpApi: event["body"] should be a JSON string.
    - For direct tests: event might already be the payload.
    """
    body = event.get("body")

    # If there's an explicit body string, parse that.
    if isinstance(body, str):
        raw_body = body
    # If body is already a dict (local testing), just use it.
    elif isinstance(body, dict):
        return body
    else:
        # Fallback: treat the whole event as the payload for local tests
        raw_body = json.dumps(event)

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning(
            "ingest.invalid_json",
            extra={"body_preview": str(raw_body)[:200]},
        )
        raise


def lambda_handler(event, context):
    logger.info(
        "ingest.lambda_start",
        extra={
            "request_id": getattr(context, "aws_request_id", None),
            "event_preview": str(event)[:500],
        },
    )

    # 1) Load environment configuration lazily
    try:
        approved_queue_url, approved_delay_seconds, idempotency_table = _load_env()
        logger.debug(
            "ingest.env_loaded",
            extra={
                "approved_queue_url": approved_queue_url,
                "approved_delay_seconds": approved_delay_seconds,
                "idempotency_table": idempotency_table,
            },
        )
    except RuntimeError as e:
        # Misconfiguration is a 500, not a 4xx
        logger.error(
            "ingest.env_error",
            extra={"error": str(e)},
        )
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "server_misconfigured"}),
        }

    # 2) Parse JSON body
    try:
        payload = _parse_body(event)
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "invalid_json"}),
        }

    # --- Start Main Logic ---
    # This try block wraps all business logic
    try:
        logger.info("ingest.payload_received", extra={"payload": payload})

        # 3) Extract required fields
        evt = payload.get("event")
        event_id = payload.get("event_id")
        user = payload.get("user") or {}
        phone = user.get("phone")
        amount = payload.get("amount")
        send_in_transit_now = bool(payload.get("send_in_transit_now"))

        if not phone or amount is None:
            logger.warning(
                "ingest.missing_fields",
                extra={
                    "event": evt,
                    "event_id": event_id,
                    "phone_present": bool(phone),
                    "amount_present": amount is not None,
                },
            )
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "missing_required_fields"}),
            }

        # 4) Optional: send instant “in transit” SMS via Twilio
        if send_in_transit_now:
            try:
                amount_float = float(amount)
            except (TypeError, ValueError):
                amount_float = None

            if amount_float is not None:
                body_text = (
                    f"🎉 Your ${amount_float:.2f} advance is on its way! "
                    "We’ve sent it to your bank. – PaySlice"
                )
            else:
                body_text = (
                    "🎉 Your advance is on its way! "
                    "We’ve sent it to your bank. – PaySlice"
                )

            try:
                resp = twilio_client.messages.create(
                    msid=twilio_conf["msid"],
                    to=phone,
                    body=body_text,
                )
                logger.info(
                    "ingest.twilio_in_transit_sent",
                    extra={"sid": resp.sid, "to": phone, "amount": amount},
                )
            except Exception as e:
                logger.error(
                    "ingest.twilio_in_transit_error",
                    extra={"error": str(e), "phone": phone, "amount": amount},
                )
                # We still continue to enqueue the delayed event.

        # 5) Always enqueue approved event for Worker (delayed SMS)
        msg_for_worker = {
            "event_id": payload.get("event_id"),
            "event": payload.get("event"),
            "user": {"phone": payload["user"]["phone"]},
            "amount": payload["amount"],
        }

        event_type = msg_for_worker.get("event")

        # Instant for advance_in_transit, delayed for everything else
        delay_seconds = 0 if event_type == "advance_in_transit" else approved_delay_seconds

        resp = sqs.send_message(
            QueueUrl=approved_queue_url,
            MessageBody=json.dumps(msg_for_worker),
            DelaySeconds=delay_seconds,
        )

        logger.info(
            "ingest.enqueued",
            extra={
                "queue_url": approved_queue_url,
                "message_id": resp["MessageId"],
                "event": event_type,
                "delay_seconds": delay_seconds,
            },
        )

        # 6) Happy path
        return {
            "statusCode": 202,
            "body": json.dumps({"queued": True}),
        }

    # This 'except' block now correctly catches errors from the 'try' block above
    except Exception as e:
        logger.error(
            "ingest.queue_error",
            extra={"error": str(e), "queue_url": approved_queue_url},
        )
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "queue_failure"}),
        }