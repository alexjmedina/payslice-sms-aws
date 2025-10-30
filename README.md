# payslice-sms-aws
PaySlice AWS SAM repository for the Twilio SMS microservice.
# PaySlice SMS Microservice (AWS SAM + Twilio)

This service sends transactional SMS via Twilio using AWS Lambda, API Gateway, and SQS.
It powers two message types:
- **Advance in Transit:** Sent instantly.
- **Advance Approved:** Sent after a 2-minute delay via SQS.

## 🧭 Architecture
Node.js / Next.js → API Gateway (/sms)
├── Lambda (ingest)
│ ├── sends instant SMS
│ └── queues delayed SMS → SQS (DelaySeconds=120)
└── Lambda (worker, SQS trigger) → Twilio API
↓
Twilio → SMS to user

## Final repo structure
payslice-sms-aws/
├─ README.md
├─ requirements.txt              # twilio, boto3, pydantic (or msgspec), httpx (optional)
├─ samconfig.toml
├─ template.yaml
├─ src/
│  ├─ ingest.py                  # POST /sms
│  ├─ worker.py                  # SQS trigger
│  ├─ status.py                  # POST /twilio/status
│  ├─ health.py                  # GET /healthz, /version
│  └─ utils/
│     ├─ __init__.py
│     ├─ logger.py
│     ├─ secrets.py
│     ├─ twilio_client.py
│     └─ idempotency.py          # DynamoDB-based (optional but recommended)
└─ tests/
   ├─ test_ingest.py
   ├─ test_worker.py
   └─ events/ (sample API Gateway/SQS events)

## Event contract (make it explicit)

To honor the “one event contract” principle, accept a single envelope with minimal required fields, and reject anything outside spec (json):

{
  "event_id": "uuid-v4",
  "event": "advance_approved" | "advance_in_transit",
  "user": { "phone": "+15555551234" },
  "amount": 185.0,                   // required for approved
  "metadata": { "source": "webapp", "correlation_id": "..." }
}


This mirrors the doc’s “one contract, two lanes” directive while keeping transactional path separate from marketing.