import json, sys, time

def log(event, **fields):
    rec = {"ts": int(time.time()), "event": event, **fields}
    print(json.dumps(rec), file=sys.stdout, flush=True)

