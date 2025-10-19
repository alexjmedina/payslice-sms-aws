from twilio.rest import Client
from .secrets import get_secrets

def get_twilio_client():
    sec = get_secrets()
    return Client(sec["TWILIO_ACCOUNT_SID"], sec["TWILIO_AUTH_TOKEN"]), sec
