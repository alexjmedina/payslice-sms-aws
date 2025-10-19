import boto3, json, os
from botocore.config import Config

_region = os.environ.get("REGION", "us-east-1")
_arn    = os.environ["SECRETS_ARN"]
_sm     = boto3.client("secretsmanager", config=Config(region_name=_region))

def get_secrets():
    val = _sm.get_secret_value(SecretId=_arn)
    return json.loads(val["SecretString"])
