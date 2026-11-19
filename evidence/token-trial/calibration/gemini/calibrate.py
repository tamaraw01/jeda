"""Record bounded usage probes without saving authorization headers."""
import hashlib
import json
import os
from pathlib import Path
import random
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
MODEL = os.environ.get('JEDA_MODEL', 'ag/claude-sonnet-4-6')
URL = os.environ.get('JEDA_ENDPOINT', 'http://localhost:20128/v1/chat/completions')
key = os.environ['HERMES_CUSTOM_9ROUTER_HERMES_API_KEY']
plan = [('short', 0), ('long', 600), ('short', 0), ('medium', 150), ('long', 600), ('medium', 150)]
random.Random(11920).shuffle(plan)
records = []
for i, (label, count) in enumerate(plan):
    payload = {'model': MODEL, 'messages': [{'role': 'system', 'content': 'Read the whole supplied context. Reply with exactly OK.'}, {'role': 'user', 'content': ''.join(f'Record {j:04d}: retained context value {j*71%997}.\n' for j in range(count)) + 'Reply OK.'}], 'temperature': 0, 'max_tokens': 12, 'stream': False, 'stream_options': {'include_usage': True}}
    data = json.dumps(payload, ensure_ascii=False).encode()
    record = {'label': label, 'request': payload, 'request_sha256': hashlib.sha256(data).hexdigest(), 'request_bytes': len(data), 'started': time.time()}
    req = urllib.request.Request(URL, data, {'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            record['response'] = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        record['error'] = type(exc).__name__ + ': ' + str(exc)[:300]
    record['seconds'] = time.time() - record['started']
    records.append(record)
    (ROOT/'records.json').write_text(json.dumps(records, indent=2))
    print(json.dumps({'index': i, 'label': label, 'bytes': len(data), 'usage': record.get('response', {}).get('usage'), 'response_model': record.get('response', {}).get('model'), 'error': record.get('error')}), flush=True)
    if record.get('error'):
        break
