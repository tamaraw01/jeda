"""Summarize reviewed, paired task totals. No network or model calls."""
import argparse
import csv
import json


def score(rows, cases, repeats):
    if not cases or len(set(cases)) != len(cases) or type(repeats) is not int or repeats < 1:
        raise ValueError("Invalid case manifest or repeats")
    expected = {(c, r, a) for c in cases for r in range(1, repeats + 1) for a in ('control', 'jeda')}
    records = {}
    for row in rows:
        if set(row) != {'case', 'repeat', 'arm', 'tokens', 'quality'}:
            raise ValueError("Expected case,repeat,arm,tokens,quality")
        try:
            key = (row['case'], int(row['repeat']), row['arm'])
            tokens = int(row['tokens'])
        except (ValueError, TypeError):
            raise ValueError("Invalid integer field") from None
        if key not in expected or key in records or tokens <= 0 or row['quality'] not in ('pass', 'fail'):
            raise ValueError("Unexpected, duplicate, or invalid record")
        records[key] = (tokens, row['quality'])
    if records.keys() != expected:
        raise ValueError("Missing required paired records")
    results = []
    for case in cases:
        totals = {a: sum(records[(case, r, a)][0] for r in range(1, repeats + 1)) for a in ('control', 'jeda')}
        results.append({'case': case, **totals, 'saved_tokens': totals['control'] - totals['jeda']})
    control = sum(x['control'] for x in results)
    jeda = sum(x['jeda'] for x in results)
    quality = all(q == 'pass' for _, q in records.values())
    return {'quality_pass': quality, 'eligible': quality and jeda < control,
            'control_tokens': control, 'jeda_tokens': jeda, 'saved_tokens': control - jeda,
            'cases': results, 'scope': 'Descriptive comparison only; not proof of production readiness.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('--cases', required=True, help='JSON array of required case IDs')
    parser.add_argument('--repeats', type=int, required=True)
    args = parser.parse_args()
    try:
        with open(args.cases, encoding='utf-8') as f:
            cases = json.load(f)
        if not isinstance(cases, list) or not all(isinstance(c, str) and c for c in cases):
            raise ValueError('Case manifest must be an array of nonempty strings')
        with open(args.csv, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            expected = ['case', 'repeat', 'arm', 'tokens', 'quality']
            if reader.fieldnames is None or len(reader.fieldnames) != len(expected) or set(reader.fieldnames) != set(expected):
                raise ValueError('CSV header must contain each required column exactly once')
            result = score(reader, cases, args.repeats)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 0 if result['eligible'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
