# payslice-sms-aws
PaySlice AWS SAM repository for the Twilio SMS microservice.
# PaySlice SMS Microservice (AWS SAM + Twilio)

This service sends transactional SMS via Twilio using AWS Lambda, API Gateway, and SQS.
It powers two message types:
- **Advance in Transit:** Sent instantly.
- **Advance Approved:** Sent after a 2-minute delay via SQS.

## 🧭 Architecture
