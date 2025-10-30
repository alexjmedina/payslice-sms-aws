import json
import os
import types
import importlib

# Target under test: src/ingest.lambda_handler
# We will monkeypatch:
#  - utils.secrets.get_twilio_secrets
#  - utils.twilio_client.build_client
#  - boto3.client("sqs") used inside ingest

class StubTwilioMsg:
    def __init__(self, sid="SMXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"):
        self.sid = sid

class StubTwilioClient:
    def __init__(self):
        self._sent = []

    def messages(self):
        return self

    # Twilio SDK uses .messages.create(...). We implement create directly.
    def create(self, to, messaging_service_sid, body):
        # Save for assertions
        self._sent.append({"to": to, "msid": messaging_service_sid, "body": body})
        return StubTwilioMsg()

class StubSQS:
    def __init__(self):
        self.sent = []

    def send_message(self, QueueUrl, MessageBody, DelaySeconds):
        self.sent.append({
            "QueueUrl": QueueUrl,
            "MessageBody": MessageBody,
            "DelaySeconds": DelaySeconds
        })
        return {"MessageId": "123"}

def _load_event(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_ingest_in_transit(monkeypatch, tmp_path):
    # Arrange env
    os.environ["APPROVED_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/471448382674/payslice-approved-queue"
    os.environ["APPROVED_DELAY_SECONDS"] = "120"
    os.environ["TWILIO_SECRET_NAME"] = "payslice/twilio/txn"
    os.environ["AWS_REGION"] = "us-east-1"

    # Monkeypatch secrets
    def fake_get_twilio_secrets(secret_name=None, region=None):
        return {
            "account_sid": "ACxxx",
            "auth_token": "tok",
            "msid": "MGxxxxxxxxxxxxxxxxxxxxx",
            "bearer": "test-bearer"
        }
    monkeypatch.setattr("src.utils.secrets.get_twilio_secrets", fake_get_twilio_secrets, raising=True)

    # Monkeypatch Twilio client builder
    stub_twilio = StubTwilioClient()
    def fake_build_client():
        return stub_twilio, {"TWILIO_MSID": "MGxxxxxxxxxxxxxxxxxxxxx", "msid": "MGxxxxxxxxxxxxxxxxxxxxx"}
    monkeypatch.setattr("src.utils.twilio_client.build_client", fake_build_client, raising=True)

    # Monkeypatch boto3 SQS client used inside ingest
    stub_sqs = StubSQS()
    class FakeBoto3:
        def client(self, name):
            assert name == "sqs"
            return stub_sqs
    monkeypatch.setattr("src.ingest.boto3", FakeBoto3(), raising=True)

    # Import (or reload) target
    ingest = importlib.reload(importlib.import_module("src.ingest"))

    # Load sample API Gateway event (in-transit → immediate send)
    event = _load_event("tests/events/api_ingest_in_transit.json")

    # Act
    resp = ingest.lambda_handler(event, None)

    # Assert
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "sid" in body
    # Ensure Twilio send happened exactly once
    assert len(stub_twilio._sent) == 1
    sent = stub_twilio._sent[0]
    assert sent["to"] == "+15555550123"
    assert sent["msid"].startswith("MG")
    assert "Ta-dah! Your advance is being sent" in sent["body"]
    # Ensure no SQS usage for in_transit
    assert len(stub_sqs.sent) == 0

def test_ingest_approved_enqueues(monkeypatch):
    # Arrange env
    os.environ["APPROVED_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/471448382674/payslice-approved-queue"
    os.environ["APPROVED_DELAY_SECONDS"] = "120"
    os.environ["TWILIO_SECRET_NAME"] = "payslice/twilio/txn"
    os.environ["AWS_REGION"] = "us-east-1"

    # Monkeypatch secrets
    def fake_get_twilio_secrets(secret_name=None, region=None):
        return {
            "account_sid": "ACxxx",
            "auth_token": "tok",
            "msid": "MGxxxxxxxxxxxxxxxxxxxxx",
            "bearer": "test-bearer"
        }
    monkeypatch.setattr("src.utils.secrets.get_twilio_secrets", fake_get_twilio_secrets, raising=True)

    # Monkeypatch Twilio client builder
    stub_twilio = StubTwilioClient()
    def fake_build_client():
        return stub_twilio, {"TWILIO_MSID": "MGxxxxxxxxxxxxxxxxxxxxx", "msid": "MGxxxxxxxxxxxxxxxxxxxxx"}
    monkeypatch.setattr("src.utils.twilio_client.build_client", fake_build_client, raising=True)

    # Monkeypatch boto3 SQS client used inside ingest
    stub_sqs = StubSQS()
    class FakeBoto3:
        def client(self, name):
            assert name == "sqs"
            return stub_sqs
    monkeypatch.setattr("src.ingest.boto3", FakeBoto3(), raising=True)

    # Reload target
    ingest = importlib.reload(importlib.import_module("src.ingest"))

    # Load sample API Gateway event (approved → enqueue)
    event = _load_event("tests/events/api_ingest_approved.json")

    # Act
    resp = ingest.lambda_handler(event, None)

    # Assert
    assert resp["statusCode"] in (200, 202)
    # Ensure nothing sent immediately
    assert len(stub_twilio._sent) == 0
    # Ensure SQS enqueued exactly once
    assert len(stub_sqs.sent) == 1
    m = stub_sqs.sent[0]
    assert m["DelaySeconds"] == 120
    body = json.loads(m["MessageBody"])
    assert body["phone"] == "+15555550123"
    assert body["amount"] == 185.0
