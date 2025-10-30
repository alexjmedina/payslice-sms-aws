"""
PaySlice SMS Microservice
=========================

Root package for the AWS-native transactional SMS microservice powering PaySlice.
This service handles secure, event-driven delivery of transactional text messages
through Twilio, using AWS SAM, Lambda, SQS, and Secrets Manager.

Modules under this package:
- ingest.py   → HTTP endpoint for event ingestion (/sms)
- worker.py   → SQS-triggered processor for delayed “Approved” messages
- status.py   → Twilio delivery status webhook (/twilio/status)
- health.py   → Health and version checks (/healthz, /version)
- utils/      → Shared helper modules (logging, secrets, Twilio client, etc.)

Environment variables expected:
  • AWS_REGION                 - AWS region for all resources
  • TWILIO_SECRET_NAME         - Name of AWS Secrets Manager secret
  • APPROVED_QUEUE_URL         - URL of SQS queue for delayed messages
  • APPROVED_DELAY_SECONDS     - Default delay for “Approved” notifications
  • IDEMPOTENCY_TABLE          - DynamoDB table for duplicate-event prevention (optional)
  • LOG_LEVEL                  - Log verbosity (default: INFO)

All handlers in this package are stateless and Lambda-optimized.
"""

__version__ = "1.0.0"
__author__ = "PaySlice Engineering"
__license__ = "MIT"

# Expose top-level package metadata only
__all__ = ["__version__", "__author__"]
