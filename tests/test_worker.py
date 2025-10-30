import json
import os
import importlib

# Target under test: src/worker.lambda_handler
# We monkeypatch:
#  - utils.twilio_client.build_client

class StubTwilioMsg:
    def __init__(self, sid="SMYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY"):
        self.sid = sid

class StubTwilioClient:
    def __init__(self):
        self.sent = []

    def messages(self):
        return self

    def create(self, to, messaging_service_sid, body):
        self.sent.append({"to": to, "msid": messaging_service_sid, "body": body})
        return StubTwilioMsg()

def _load_event(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_worker_sends_approved(monkeypatch):
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["TWILIO_SECRET_NAME"] = "payslice/twilio/txn"

    stub = StubTwilioClient()
    def fake_build_client():
        return stub, {"TWILIO_MSID": "MGxxxxxxxxxxxxxxxxxxxxx", "msid": "MGxxxxxxxxxxxxxxxxxxxxx"}
    monkeypatch.setattr("src.utils.twilio_client.build_client", fake_build_client, raising=True)

    worker = importlib.reload(importlib.import_module("src.worker"))
    event = _load_event("tests/events/sqs_worker_event.json")

    resp = worker.lambda_handler(event, None)
    assert resp["statusCode"] == 200
    assert len(stub.sent) == 1
    msg = stub.sent[0]
    assert msg["to"] == "+15555550123"
    assert msg["msid"].startswith("MG")
    assert "approved" in msg["body"].lower()
    assert "$185.00" in msg["body"]
