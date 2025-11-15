from twilio.rest import Client as TwilioClient

from utils.secrets import get_twilio_secrets


def build_client():
    secrets = get_twilio_secrets()
    client = TwilioClient(secrets.account_sid, secrets.auth_token)
    conf = {
        "messaging_service_sid": secrets.msid,
    }
    return client, conf
