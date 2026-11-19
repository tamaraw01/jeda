"""Audit raw gateway accounting and replay tool execution from recorded responses."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def evaluate(directory):
    root = Path(directory)
    plan = json.loads((root / 'plan.json').read_text())
    frozen = root / 'frozen'
    for name, expected in plan['source_sha256'].items():
        assert hashlib.sha256((frozen / name).read_bytes()).hexdigest() == expected, name
    sys.path.insert(0, str(frozen))
    for name in ('runner', 'fixtures', 'summarize'):
        sys.modules.pop(name, None)
    import runner
    import summarize
    cases = {c['id']: c for c in runner.load_cases(plan['scope'])}
    expected = {(c, n, a) for c in plan['cases'] for n in range(1, plan['repeats'] + 1) for a in plan['arms']}
    records = [json.loads(p.read_text()) for p in sorted((root / 'results').glob('*.json'))]
    keys = [(r['case'], r['repeat'], r['arm']) for r in records]
    assert len(keys) == len(set(keys)) and set(keys) == expected, 'incomplete or duplicate matrix'
    audited = []
    for row in records:
        assert row['plan_sha256'] == plan['plan_sha256']
        assert row['calls'], 'missing calls'
        tool, out = runner.sandbox(cases[row['case']])
        actions = []
        final = ''
        tokens = 0
        labels = set()
        for call in row['calls']:
            payload, response = call['request'], call['response']
            wire = json.dumps(payload, ensure_ascii=False)
            assert runner.sha(wire) == call['request_sha256']
            assert len(wire.encode()) == call['request_bytes']
            assert runner.sha(json.dumps(response, sort_keys=True)) == call['response_sha256']
            assert payload['model'] == plan['model']
            tokens += runner.usage_tokens(response.get('usage'))
            labels.add(response.get('model'))
            message = response['choices'][0]['message']
            if message.get('tool_calls'):
                for operation in message['tool_calls']:
                    try:
                        args = json.loads(operation['function'].get('arguments') or '{}')
                    except ValueError:
                        args = {}
                    tool(operation['function']['name'], args, actions)
            else:
                final = message.get('content') or ''
        assert actions == row['actions'], 'recorded actions disagree with response replay'
        checks, quality = runner.rubric(cases[row['case']], actions, out, final)
        audited.append(dict(row, tokens=tokens, quality=quality and not row.get('error'), checks=checks,
                            response_models=sorted(labels)))
    report = {'scope': plan['scope'], 'sessions': len(audited), 'accounting': 'gateway reported; no external billing reconciliation',
              'source_hashes_verified': True, 'response_replay_verified': True, 'arms': {}}
    for arm in plan['arms']:
        rows = [r for r in audited if r['arm'] == arm]
        report['arms'][arm] = {'tokens': sum(r['tokens'] for r in rows), 'quality_passes': sum(r['quality'] for r in rows),
                               'sessions': len(rows), 'calls': sum(len(r['calls']) for r in rows),
                               'response_models': sorted({m for r in rows for m in r['response_models']}),
                               'failures': [{'case': r['case'], 'repeat': r['repeat'], 'checks': r['checks']} for r in rows if not r['quality']]}
    control = report['arms']['control']['tokens']
    for arm in ('skill', 'candidate'):
        result = report['arms'][arm]
        result['saving_pct'] = round(100 * (control - result['tokens']) / control, 2)
        result['ci95_pct'] = summarize.cluster_ci(audited, plan['cases'], arm)
    report['savings_claim_pass'] = False
    report['limitations'] = ['Synthetic extraction tasks only; six cases per split.',
                             'Held-out inference was not used to tune instructions; both splits ran concurrently after freeze.',
                             'Quality failures prevent a quality-parity claim.',
                             'Gateway usage has not been reconciled against provider billing.',
                             'Confidence intervals are exploratory with only six clusters.']
    (root / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    sys.path.pop(0)


if __name__ == '__main__':
    for directory in sys.argv[1:]:
        evaluate(directory)
