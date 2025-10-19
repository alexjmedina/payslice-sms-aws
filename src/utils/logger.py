import json, datetime
def log(event, **kwargs):
    print(json.dumps({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "event": event,
        **kwargs
    }))
