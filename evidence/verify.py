"""Recheck saved artifacts and action order without model calls."""
import ast
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent / 'corrected'


def code_safe(content):
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False
    allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Compare, ast.Name, ast.Load, ast.Constant, ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq)
    return (len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef)
            and tree.body[0].name == 'overdue'
            and all(isinstance(node, allowed) for node in ast.walk(tree))
            and all(not isinstance(node, ast.Name) or node.id in {'age', 'threshold'} for node in ast.walk(tree)))

def main():
    plan = json.loads((ROOT / 'plan.json').read_text())
    expected_keys = {(c, r, a) for c in plan['cases'] for r in range(1, plan['repeats'] + 1) for a in plan['arms']}
    records = [json.loads(p.read_text()) for p in (ROOT / 'results').glob('*.json')]
    keys = [(r['case'], r['repeat'], r['arm']) for r in records]
    assert len(keys) == len(set(keys)) and set(keys) == expected_keys, 'Incomplete trial'
    checks = []
    for record in records:
        case, repeat, arm = record['case'], record['repeat'], record['arm']
        sandbox = ROOT / 'sandboxes' / f'{case}-{repeat}-{arm}'
        actions = record['actions']
        writes = [i for i, a in enumerate(actions) if a['name'] == 'write_file' and a['ok']]
        later = actions[writes[-1] + 1:] if writes else []
        if case == 'invoices':
            with (sandbox / 'invoices.csv').open(newline='') as f:
                expected = [r['id'] for r in csv.DictReader(f) if int(r['age_days']) > 45 and r['status'] == 'open']
            actual = json.loads((sandbox / 'answer.json').read_text())
            artifact = actual == expected
            details = {'expected_count': len(expected), 'actual_count': len(actual), 'missing': sorted(set(expected) - set(actual)), 'unexpected': sorted(set(actual) - set(expected))}
        elif case == 'policy':
            expected = {'general_days': 30, 'legacy_days': 90, 'exceptions': ['Disputed records remain until the dispute closes.', 'A legal hold overrides both periods.']}
            artifact = json.loads((sandbox / 'answer.json').read_text()) == expected
            details = {}
        else:
            # Execute only code matching the runner's restricted grammar.
            assert code_safe((sandbox / 'calc.py').read_text()), 'Unsafe generated code'
            result = subprocess.run([sys.executable, '-I', '-c', "import sys,runpy;sys.path.insert(0,'.');runpy.run_path('checks.py',run_name='__main__')"], cwd=sandbox, capture_output=True, text=True, timeout=10)
            artifact = result.returncode == 0
            details = {'test_exit_code': result.returncode}
        if case == 'repair':
            verified = any(a['name'] == 'run_tests' and a['ok'] and a['result'].get('exit_code') == 0 for a in later)
        else:
            verified = any(a['name'] == 'read_file' and a['ok'] and a['args'].get('path') == 'answer.json' for a in later)
        sources_ok = True
        for action in actions:
            if action['name'] == 'read_file' and action['ok']:
                name = action['args']['path']
                if name not in {'answer.json', 'calc.py'}:
                    sources_ok = sources_ok and (sandbox / name).read_text() == action['result']
        checks.append({'case': case, 'repeat': repeat, 'arm': arm, 'artifact': artifact, 'verification_after_last_write': verified, 'sources_match_reads': sources_ok, 'quality': bool(artifact and verified and sources_ok and all(a['ok'] for a in actions) and record.get('final')), 'details': details})
    summary = {'sessions': len(checks), 'passes': {a: sum(r['quality'] for r in checks if r['arm'] == a) for a in plan['arms']}, 'artifact_passes': sum(r['artifact'] for r in checks), 'tool_calls': {a: sum(len(r['actions']) for r in records if r['arm'] == a) for a in plan['arms']}, 'request_bytes': {a: sum(r['request_bytes'] for r in records if r['arm'] == a) for a in plan['arms']}, 'usage_eligible': False, 'release': 'HOLD', 'checks': checks}
    assert summary['passes'] == {'control': 5, 'jeda': 6}, 'Recorded outcome changed'
    assert summary['tool_calls'] == {'control': 24, 'jeda': 20}
    assert summary['request_bytes'] == {'control': 95587, 'jeda': 136072}
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
