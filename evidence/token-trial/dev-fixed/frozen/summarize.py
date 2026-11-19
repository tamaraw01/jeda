"""Validate a frozen run and report paired token savings with a cluster bootstrap.

    python summarize.py --output runs/dev [--calibrated]

Everything is recomputed from raw records: tokens from response usage, hashes from
the stored payloads, quality from actions plus a re-derived artifact. Stored
`tokens` and `quality` fields are never trusted.

Quality is final-outcome only: correct artifact, read-back after the last write,
required sources read before that write, intact source reads, final message.
Failed-then-corrected calls stay in the token total and are reported separately
as process noise. Gates are evaluated per treatment arm; `pass` is the AND of all.

--calibrated asserts accounting was checked against an external source. It is never
inferred: gateway usage is not billing reconciliation.
"""
import argparse
import json
from pathlib import Path
import random
import statistics
import sys

import runner

TREATMENTS = ('skill', 'candidate')
BOOTSTRAP = 2000
BOOTSTRAP_SEED = 7717
MIN_SAVING_PCT = 10.0


def usage_tokens(response):
    usage = (response or {}).get('usage')
    if not isinstance(usage, dict):
        return None
    values = [usage.get(k) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')]
    if not all(type(v) is int and v >= 0 for v in values) or values[2] != values[0] + values[1]:
        return None
    return values[2]


def audit(row, cases):
    """Recompute one record. Returns (tokens, quality, problems, checks)."""
    problems = []
    case = cases.get(row['case'])
    if case is None:
        return 0, False, ['unknown case'], {}
    if not row.get('calls'):
        problems.append('no calls')
    for index, entry in enumerate(row.get('calls') or []):
        request = entry.get('request')
        expected_hash = runner.sha(json.dumps(request, ensure_ascii=False))
        if entry.get('request_sha256') != expected_hash:
            problems.append('call %d request hash mismatch' % index)
        if entry.get('request_bytes') != len(json.dumps(request, ensure_ascii=False).encode()):
            problems.append('call %d request byte count mismatch' % index)
        response = entry.get('response')
        response_hash = runner.sha(json.dumps(response, sort_keys=True))
        if entry.get('response_sha256') != response_hash:
            problems.append('call %d response hash mismatch' % index)
        tokens = usage_tokens(response)
        if tokens is None:
            problems.append('call %d usage missing or inconsistent' % index)
    if row.get('error'):
        problems.append('error: %s' % row['error'])
    tokens = sum(usage_tokens(e.get('response')) or 0 for e in row.get('calls') or [])
    actions = row.get('actions') or []
    last_write = max((i for i, a in enumerate(actions) if a['name'] == 'write_answer' and a['ok']), default=-1)
    artifact = None
    if last_write >= 0:
        try:
            artifact = json.loads(actions[last_write]['args']['content'])
        except (ValueError, KeyError):
            artifact = None
    reads = [a for a in actions if a['name'] == 'read_source' and a['ok']]
    before = {a['args'].get('id') for a in actions[:last_write] if a['name'] == 'read_source' and a['ok']}
    checks = {
        'artifact': artifact == case['expected'],
        'read_back': any(a['name'] == 'read_answer' and a['ok'] and a['result'] == actions[last_write]['args']['content']
                         for a in actions[last_write + 1:]) if last_write >= 0 else False,
        'required_sources_before_write': set(case.get('required_sources', [])) <= before,
        'sources_intact': all(a['result'].get('content') == case['sources'][a['args']['id']]['content'] for a in reads),
        'final': bool(row.get('final')),
    }
    quality = all(checks.values()) and not any(p.startswith(('error', 'no calls', 'call')) for p in problems)
    return tokens, quality, problems, checks


def load(output, scope=None):
    output = Path(output)
    plan = runner.load_plan(output)
    cases = {c['id']: c for c in runner.load_cases(plan['scope'])}
    expected = {(c, r, a) for c in plan['cases'] for r in range(1, plan['repeats'] + 1) for a in plan['arms']}
    rows = []
    for path in sorted((output / 'results').glob('*.json')):
        try:
            rows.append(json.loads(path.read_text()))
        except ValueError:
            raise SystemExit('unreadable record %s' % path)
    keys = [(r['case'], r['repeat'], r['arm']) for r in rows]
    if len(keys) != len(set(keys)):
        raise SystemExit('duplicate rows: %s' % sorted({k for k in keys if keys.count(k) > 1}))
    if set(keys) != expected:
        raise SystemExit('matrix incomplete: %d/%d, missing %s, unexpected %s'
                         % (len(set(keys) & expected), len(expected),
                            sorted(expected - set(keys))[:8], sorted(set(keys) - expected)[:8]))
    for r in rows:
        if r.get('plan_sha256') != plan['plan_sha256']:
            raise SystemExit('%s-%d-%s was produced under another plan' % (r['case'], r['repeat'], r['arm']))
    return plan, rows, cases


def pairs(rows, case, arm):
    def tokens(row):
        if 'tokens' in row:
            return row['tokens']
        return sum(usage_tokens(entry.get('response')) or 0 for entry in row.get('calls', []))
    out = []
    for repeat in sorted({r['repeat'] for r in rows if r['case'] == case}):
        pair = {r['arm']: r for r in rows if r['case'] == case and r['repeat'] == repeat}
        if 'control' in pair and arm in pair:
            out.append((tokens(pair['control']), tokens(pair[arm])))
    return out


def percent(control, treatment):
    return 100.0 * (control - treatment) / control if control else 0.0


def cluster_ci(rows, cases, arm, seed=BOOTSTRAP_SEED):
    """Percentile CI of pooled savings percent over case-cluster resamples."""
    per_case = {case: (sum(p[0] for p in pairs(rows, case, arm)), sum(p[1] for p in pairs(rows, case, arm)))
                for case in cases}
    rng = random.Random(seed)
    samples = []
    for _ in range(BOOTSTRAP):
        drawn = [rng.choice(cases) for _ in cases]
        control = sum(per_case[c][0] for c in drawn)
        treatment = sum(per_case[c][1] for c in drawn)
        if control:
            samples.append(percent(control, treatment))
    samples.sort()
    if not samples:
        return [0.0, 0.0]
    return [round(samples[int(0.025 * (len(samples) - 1))], 2), round(samples[int(0.975 * (len(samples) - 1))], 2)]


def summarize(plan, rows, cases=None, calibrated=False):
    cases = cases or {c['id']: c for c in runner.load_cases(plan['scope'])}
    scope_cases = plan['cases']
    audit_rows = []
    for row in rows:
        tokens, quality, problems, checks = audit(row, cases)
        audit_rows.append(dict(row, tokens=tokens, quality=quality, checks=checks, problems=problems))
    failures = [{'case': r['case'], 'repeat': r['repeat'], 'arm': r['arm'], 'checks': r['checks'],
                 'problems': r['problems']} for r in audit_rows if not r['quality']]
    expected_quality = len(scope_cases) * plan['repeats']
    report = {
        'scope': plan['scope'], 'model': plan['model'], 'plan_sha256': plan['plan_sha256'],
        'decision': plan.get('decision'), 'rows': len(rows), 'repeats': plan['repeats'],
        'tokens_total': {a: sum(r['tokens'] for r in audit_rows if r['arm'] == a) for a in plan['arms']},
        'quality_passes': {a: sum(1 for r in audit_rows if r['arm'] == a and r['quality']) for a in plan['arms']},
        'quality_expected': expected_quality,
        'clean_rows': {a: sum(1 for r in audit_rows if r['arm'] == a and not r['problems']) for a in plan['arms']},
        'quality_failures': failures,
        'arms': {},
    }
    for arm in TREATMENTS:
        deltas, per_case = [], []
        for case in scope_cases:
            p = pairs(audit_rows, case, arm)
            saved = [c - t for c, t in p]
            deltas.extend(saved)
            per_case.append({'case': case, 'control_tokens': sum(x[0] for x in p), 'treatment_tokens': sum(x[1] for x in p),
                             'median_saved_tokens': statistics.median(saved) if saved else None,
                             'saving_pct': round(percent(sum(x[0] for x in p), sum(x[1] for x in p)), 2)})
        control, treatment = report['tokens_total']['control'], report['tokens_total'][arm]
        report['arms'][arm] = {
            'total_saving_pct': round(percent(control, treatment), 2),
            'median_paired_saved_tokens': statistics.median(deltas) if deltas else None,
            'ci95_pct': cluster_ci(audit_rows, scope_cases, arm),
            'per_case': per_case,
        }
    gates = {'complete_matrix': True, 'usage_complete': not failures or all(
        not any(p.startswith(('usage', 'call')) for p in f['problems']) for f in failures),
        'accounting_calibrated': bool(calibrated)}
    for arm in TREATMENTS:
        stats = report['arms'][arm]
        gates['quality_%s' % arm] = report['quality_passes'][arm] == expected_quality
        gates['saving_%s' % arm] = stats['total_saving_pct'] >= MIN_SAVING_PCT and stats['ci95_pct'][0] > 0
    report['gates'] = gates
    report['pass'] = all(gates.values())
    report['accounting_note'] = ('prompt+completion recomputed from raw usage, total consistency enforced; '
                                 + ('external calibration asserted by caller' if calibrated
                                    else 'NOT externally calibrated, no billing reconciliation'))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Summarize a completed frozen run.')
    parser.add_argument('--output', required=True)
    parser.add_argument('--calibrated', action='store_true', help='accounting was checked against an external source')
    args = parser.parse_args(argv)
    plan, rows, cases = load(args.output)
    report = summarize(plan, rows, cases, calibrated=args.calibrated)
    runner.atomic_write(Path(args.output) / 'summary.json', json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
