"""
PaySlice SMS Microservice Utilities
===================================

This package provides shared helper modules for the PaySlice AWS-native
transactional SMS microservice. It includes:

- logger.py          → structured JSON logging
- secrets.py         → AWS Secrets Manager integration
- twilio_client.py   → authenticated Twilio client builder
- idempotency.py     → DynamoDB-based duplicate-event guard

All functions in this package are stateless and thread-safe, suitable for
AWS Lambda execution.
"""

import logging
import os
import sys

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
# We use structured JSON logs for CloudWatch and other downstream log systems.
# Log level can be changed by setting LOG_LEVEL environment variable.

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

_handler = logging.StreamHandler(sys.stdout)
_formatter = logging.Formatter(
    fmt='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
_handler.setFormatter(_formatter)

logger = logging.getLogger("payslice")
logger.setLevel(LOG_LEVEL)
logger.addHandler(_handler)
logger.propagate = False

# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------
__all__ = [
    "logger",
]
