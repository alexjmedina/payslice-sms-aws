from twilio.rest import Client
from .secrets import get_twilio_secrets

def build_client():
    s = get_twilio_secrets()
    return Client(s["account_sid"], s["auth_token"]), s
