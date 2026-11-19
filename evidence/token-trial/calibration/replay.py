"""Replay the four historical probe payloads and compare accounting per route."""
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
URL = os.environ.get('JEDA_ENDPOINT', 'http://localhost:20128/v1/chat/completions')
key = os.environ['HERMES_CUSTOM_9ROUTER_HERMES_API_KEY']
saved = json.loads((ROOT.parent/'jeda-direct/probe.json').read_text())
seen = {}
for record in saved:
    seen.setdefault(record['request_sha256'], record['request'])
payloads = list(seen.items())
records = []
for model in ('hermes-combo', 'ag/claude-sonnet-4-6', 'ag/claude-opus-4-6-thinking'):
    for sha, original in payloads:
        payload = dict(original, model=model, stream=False, stream_options={'include_usage': True})
        data = json.dumps(payload, ensure_ascii=False).encode()
        record = {'model': model, 'payload_sha256': sha, 'request_bytes': len(data)}
        req = urllib.request.Request(URL, data, {'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                record['response'] = json.load(response)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            record['error'] = type(exc).__name__+': '+str(exc)[:200]
        records.append(record)
        (ROOT/'replay.json').write_text(json.dumps(records, indent=2))
        usage = record.get('response', {}).get('usage') or {}
        print(json.dumps({'model': model, 'sha': sha[:12], 'bytes': len(data), 'prompt': usage.get('prompt_tokens'), 'label': record.get('response', {}).get('model'), 'error': record.get('error')}), flush=True)
