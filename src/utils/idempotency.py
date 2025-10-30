import os, time, boto3
from botocore.exceptions import ClientError
_TBL = os.getenv("IDEMPOTENCY_TABLE")

def was_processed(event_id:str, ttl_secs:int=86400)->bool:
    if not _TBL: return False
    ddb = boto3.client("dynamodb")
    try:
        resp = ddb.put_item(
            TableName=_TBL,
            Item={"pk":{"S":event_id}, "exp":{"N":str(int(time.time())+ttl_secs)}},
            ConditionExpression="attribute_not_exists(pk)"
        )
        return False
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return True
        raise
