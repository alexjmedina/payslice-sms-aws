# payslice-sms-aws
PaySlice AWS SAM repository for the Twilio SMS microservice.
# PaySlice SMS Microservice (AWS SAM + Twilio)
# payslice-sms-aws

PaySlice SMS Microservice — AWS SAM + Twilio

This repository contains an AWS Serverless microservice that sends transactional SMS messages via Twilio. It is designed to receive a single, well-defined event envelope from the PaySlice Vercel application and handle two message types:

- Advance in Transit — sent instantly.
- Advance Approved — queued with a 2-minute delay (via SQS) and sent by a worker Lambda.

**Contents**

- `template.yaml` — AWS SAM template defining Lambdas, SQS, IAM roles, and API Gateway.
- `samconfig.toml` — SAM deployment configuration.
- `requirements.txt` — Python dependencies used by Lambdas (Twilio, boto3, etc.).
- `src/` — Lambda source code:
  - `ingest.py` — API handler (POST /sms) that validates events, sends immediate SMS for `advance_in_transit`, and enqueues `advance_approved` messages to SQS with `DelaySeconds=120`.
  - `worker.py` — SQS-triggered Lambda that sends SMS via Twilio for delayed messages.
  - `status.py` — optional endpoint for Twilio status callbacks (POST /twilio/status).
  - `health.py` — health and version endpoints (GET /healthz, /version).
  - `utils/` — helper modules (`logger.py`, `secrets.py`, `twilio_client.py`, `idempotency.py`).
- `tests/` — unit tests and sample event payloads in `tests/events/`.

**High-level Architecture**

`Vercel App (POST /sms)` → `API Gateway` → `ingest` Lambda
- `ingest` Lambda: immediately sends `advance_in_transit` messages via Twilio; for `advance_approved` it queues the envelope to `SQS` with a 120s delay.
- `worker` Lambda: triggered by SQS, sends the actual SMS via Twilio and optionally emits delivery status events.

Twilio then delivers SMS to the recipient's handset and may POST delivery events to `/twilio/status` if configured.

**Event Contract**

All incoming payloads must conform to a single JSON envelope. The service validates the envelope strictly and rejects anything outside the contract with HTTP 400.

Required envelope shape:

```json
{
  "event_id": "<uuid-v4>",
  "event": "advance_in_transit" | "advance_approved",
  "user": { "phone": "+{E.164}" },
  "amount": <number>,                    
  "metadata": { "source": "webapp", "correlation_id": "<string>" }
}
```

- `event_id` (string, uuid-v4): Unique idempotency key for the envelope. Required.
- `event` (string): Must be either `advance_in_transit` or `advance_approved`.
- `user.phone` (string): Recipient phone in E.164 format (e.g. `+15555551234`). Required.
- `amount` (number): Required for `advance_approved` messages (the approved amount shown in the SMS). Optional for `advance_in_transit` or may be required depending on business rules — validation is implemented in `ingest.py`.
- `metadata` (object): Free-form object with `source`, `correlation_id`, or additional tracking fields.

Example — `advance_in_transit` (instant):

```json
{
  "event_id": "6a9f1c2a-1234-4b3a-9d8e-1f2e3d4c5b6a",
  "event": "advance_in_transit",
  "user": { "phone": "+15555551234" },
  "metadata": { "source": "webapp", "correlation_id": "abc-123" }
}
```

Example — `advance_approved` (delayed via SQS):

```json
{
  "event_id": "a1b2c3d4-5678-4e9a-bc12-34567890abcd",
  "event": "advance_approved",
  "user": { "phone": "+15555551234" },
  "amount": 185.0,
  "metadata": { "source": "webapp", "correlation_id": "def-456" }
}
```

Note: The `ingest` function enforces the schema and uses `event_id` for idempotency (see `utils/idempotency.py` if enabled).

**Environment & Secrets**

- `TWILIO_ACCOUNT_SID` — Twilio Account SID (string).
- `TWILIO_AUTH_TOKEN` — Twilio Auth Token (string).
- `TWILIO_FROM` — Sender phone number (E.164) configured in Twilio.
- AWS Roles/Permissions: Lambda needs access to SQS (SendMessage), CloudWatch Logs, and optionally DynamoDB (if using idempotency), plus permission to read secrets from Secrets Manager if secrets are stored there.

Set these variables locally when developing or configure them in your deployment pipeline / SAM template.

**Local Development**

- Create a Python virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- Run unit tests:

```bash
pytest -q
```

- Use SAM CLI to invoke Lambdas locally with sample events in `tests/events/`:

```bash
sam build
sam local invoke IngestFunction --event tests/events/api_ingest_in_transit.json
sam local invoke WorkerFunction --event tests/events/sqs_worker_event.json
```

Replace the function logical names with those from `template.yaml` if different.

**Testing**

- Unit tests live in `tests/` and use `pytest`. Sample event payloads are under `tests/events/`.
- Add tests for validation and idempotency where applicable.

**Deployment**

1. Build and package with SAM:

```bash
sam build
sam deploy --guided
```

2. Ensure `samconfig.toml` is configured for your account/region and that the IAM user/role used for deployment has sufficient privileges for CloudFormation, S3, Lambda, SQS, IAM, and Secrets Manager (if used).

**Operational Notes**

- SQS Delay: `advance_approved` messages are enqueued with `DelaySeconds=120` to implement a 2-minute delay before the worker picks them up.
- Idempotency: `event_id` should be used to deduplicate messages. Optionally enable idempotency backed by DynamoDB using `utils/idempotency.py`.
- Monitoring: CloudWatch Logs and Metrics for Lambda invocations and SQS queue depth are recommended.

**Contributing**

- File an issue or open a PR for changes. Keep commits small and tests passing.
- Follow the existing Python coding style in `src/` and add tests for new behavior.

**License & Contact**

- See the repository `LICENSE` file for licensing details.
- For questions contact the repository owner or maintainer.

---

This README documents the expected event contract and operational details required to integrate the PaySlice Vercel app with this microservice.