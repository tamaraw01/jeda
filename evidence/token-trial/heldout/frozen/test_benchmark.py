import json
import random
import tempfile
import unittest
from pathlib import Path

import runner
import summarize
from fixtures import DEV, HELDOUT


def reply(message, usage=(100, 20)):
    return {'choices': [{'message': message}], 'usage': {'prompt_tokens': usage[0], 'completion_tokens': usage[1],
                                                         'total_tokens': usage[0] + usage[1]}}


def call(name, args=None, id='c1'):
    return {'id': id, 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args or {})}}


def scripted(case, read_back=True, artifact=None, skip_read=False, usage=(100, 20)):
    """Fake transport that walks the intended tool order, then finishes."""
    body = json.dumps(case['expected'] if artifact is None else artifact)
    steps = ([] if skip_read else [call('read_source', {'id': next(iter(case['sources']))})])
    steps.append(call('write_answer', {'content': body}, 'c2'))
    if read_back:
        steps.append(call('read_answer', id='c3'))
    state = {'n': 0}

    def transport(payload):
        step = state['n']
        state['n'] += 1
        if step < len(steps):
            return reply({'role': 'assistant', 'tool_calls': [steps[step]]}, usage)
        return reply({'role': 'assistant', 'content': 'Done.'}, (7, 3))
    return transport


class RunCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.plan = runner.make_plan('dev', 1)
        runner.atomic_write(self.out / 'plan.json', json.dumps(self.plan))

    def tearDown(self):
        self.tmp.cleanup()

    def run_case(self, case, **kw):
        return runner.run_one(self.plan, dict(case, history=''), 1, 'control', self.out,
                              transport=scripted(case, **kw), prompts={'control': '', 'skill': '', 'candidate': ''})

    def test_clean_trial_passes_and_sums_output_tokens(self):
        case = next(c for c in DEV if not c['stale'])
        record = self.run_case(case)
        self.assertTrue(record['quality'], record.get('checks'))
        self.assertEqual(record['tokens'], (100 + 20) * 3 + 10)   # every call, prompt and completion
        for entry in record['calls']:
            self.assertEqual(entry['request_sha256'], runner.sha(json.dumps(entry['request'], ensure_ascii=False)))
            self.assertIn('stream_options', entry['request'])
            self.assertIs(entry['request']['stream'], False)

    def test_stale_case_without_read_fails(self):
        case = next(c for c in runner.load_cases('dev') if c['stale'])
        record = self.run_case(case, skip_read=True)
        self.assertFalse(record['checks']['required_sources_before_write'])
        self.assertFalse(record['quality'])

    def test_cached_valid_case_may_skip_read(self):
        case = next(c for c in DEV if c['id'] == 'cached-valid')
        record = self.run_case(case, skip_read=True)
        self.assertTrue(record['checks']['required_sources_before_write'])
        self.assertTrue(record['quality'], record.get('checks'))

    def test_no_read_back_fails(self):
        case = next(c for c in DEV if not c['stale'])
        record = self.run_case(case, read_back=False)
        self.assertFalse(record['checks']['read_back'])
        self.assertFalse(record['quality'])

    def test_wrong_artifact_fails(self):
        case = next(c for c in DEV if not c['stale'])
        record = self.run_case(case, artifact=['nope'])
        self.assertFalse(record['checks']['artifact'])
        self.assertFalse(record['quality'])

    def test_leading_zero_and_final_row(self):
        case = next(c for c in DEV if c['id'] == 'leading-zero-final')
        record = self.run_case(case)
        self.assertTrue(record['quality'], record.get('checks'))
        self.assertEqual(json.loads(record['actions'][1]['args']['content']), ['007', '039'])

    def test_missing_usage_blocks_result(self):
        case = next(c for c in DEV if not c['stale'])
        broken = scripted(case)
        record = runner.run_one(self.plan, dict(case, history=''), 1, 'control', self.out,
                                transport=lambda p: {k: v for k, v in broken(p).items() if k != 'usage'},
                                prompts={'control': '', 'skill': '', 'candidate': ''})
        self.assertIn('usage', record['error'])
        self.assertFalse(record['quality'])

    def test_inconsistent_usage_blocks_result(self):
        case = next(c for c in DEV if not c['stale'])
        base = scripted(case)
        record = runner.run_one(self.plan, dict(case, history=''), 1, 'control', self.out,
                                transport=lambda p: dict(base(p), usage={'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 999}),
                                prompts={'control': '', 'skill': '', 'candidate': ''})
        self.assertIn('usage total 999', record['error'])
        self.assertFalse(record['quality'])

    def test_failed_action_fails_quality(self):
        case = next(c for c in DEV if not c['stale'])
        tool, out = runner.sandbox(case)
        actions = []
        tool('read_answer', {}, actions)                       # nothing written yet
        tool('read_source', {'id': 'nope'}, actions)
        checks, ok = runner.rubric(case, actions, out, 'done')
        self.assertFalse(checks['no_failed_action'])
        self.assertFalse(ok)

    def test_source_reads_are_copied_and_checked(self):
        case = next(c for c in DEV if not c['stale'])
        record = self.run_case(case)
        self.assertTrue(record['checks']['sources_intact'])
        key = record['actions'][0]['args']['id']
        self.assertEqual(record['actions'][0]['result']['content'], case['sources'][key]['content'])

    def test_resume_skips_finished_and_rejects_other_plan(self):
        case = next(c for c in DEV if not c['stale'])
        self.run_case(case)
        again = runner.run_one(self.plan, dict(case, history=''), 1, 'control', self.out,
                               transport=lambda p: self.fail('should not be called'))
        self.assertTrue(again['quality'])
        other = dict(self.plan, plan_sha256='0' * 64)
        with self.assertRaises(SystemExit):
            runner.run_one(other, dict(case, history=''), 1, 'control', self.out, transport=lambda p: None)

    def test_plan_hash_detects_edit(self):
        path = self.out / 'plan.json'
        tampered = dict(self.plan, repeats=9)
        path.write_text(json.dumps(tampered))
        with self.assertRaises(SystemExit):
            runner.load_plan(self.out)


class FixtureTests(unittest.TestCase):
    def test_six_each_and_disjoint(self):
        self.assertEqual((len(DEV), len(HELDOUT)), (6, 6))
        self.assertFalse({c['id'] for c in DEV} & {c['id'] for c in HELDOUT})
        self.assertEqual(len({c['id'] for c in DEV + HELDOUT}), 12)

    def test_every_case_is_well_formed(self):
        for case in DEV + HELDOUT:
            self.assertTrue(case['prior'] and case['task'] and case['sources'])
            self.assertIn('expected', case)
            for source in case['sources'].values():
                self.assertIn(source['format'], ('text', 'json'))
        self.assertTrue(any(c['stale'] for c in DEV))
        self.assertFalse(next(c for c in DEV if c['id'] == 'cached-valid')['stale'])

    def test_plan_freezes_settings_and_hashes(self):
        plan = runner.make_plan('heldout', 2)
        self.assertEqual(plan['settings']['max_calls'], 8)
        self.assertEqual(plan['settings']['timeout_s'], 90)
        self.assertEqual(plan['settings']['concurrency'], 2)
        self.assertEqual(plan['model'], 'ag/claude-sonnet-4-6')
        self.assertEqual(plan['plan_sha256'], runner.hash_plan(plan))


def matrix(rows_per_case=1, repeats=3, saving=0.2, quality=True):
    rows, plan = [], runner.make_plan('dev', repeats)
    for case, repeat, arm in plan_cases(plan, rows_per_case):
        tokens = 100
        if arm != 'control':
            tokens = int(100 * (1 - saving))
        rows.append({'case': case, 'repeat': repeat, 'arm': arm, 'tokens': tokens, 'quality': quality,
                     'plan_sha256': plan['plan_sha256'], 'calls': [{}]})
    return plan, rows


def plan_cases(plan, repeats):
    return [(c, r, a) for c in plan['cases'] for r in range(1, plan['repeats'] + 1) for a in plan['arms']][:len(plan['cases']) * plan['repeats'] * 3] if repeats else []


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rows, plan=None):
        plan = plan or runner.make_plan('dev', 3)
        runner.atomic_write(self.out / 'plan.json', json.dumps(plan))
        for row in rows:
            runner.atomic_write(self.out / 'results' / ('%s-%d-%s.json' % (row['case'], row['repeat'], row['arm'])), json.dumps(row))
        return plan

    def full_rows(self, plan=None, **kw):
        plan = plan or runner.make_plan('dev', 3)
        fixture_cases = {c['id']: c for c in runner.load_cases(plan['scope'])}
        rows = []
        for index, case_id in enumerate(plan['cases']):
            case = fixture_cases[case_id]
            content = json.dumps(case['expected'])
            for repeat in range(1, plan['repeats'] + 1):
                for arm in plan['arms']:
                    saved = 0 if arm == 'control' else 12 + index * 6
                    total = 120 - saved
                    response = {'usage': {'prompt_tokens': total - 10, 'completion_tokens': 10,
                                          'total_tokens': total}}
                    request = {'case': case_id, 'repeat': repeat, 'arm': arm}
                    call_row = {'request': request, 'request_sha256': runner.sha(json.dumps(request, ensure_ascii=False)),
                                'request_bytes': len(json.dumps(request, ensure_ascii=False).encode()),
                                'response': response, 'response_sha256': runner.sha(json.dumps(response, sort_keys=True))}
                    actions = []
                    for source_id in case.get('required_sources', []):
                        actions.append({'name': 'read_source', 'args': {'id': source_id},
                                        'result': {'id': source_id, **case['sources'][source_id]}, 'ok': True})
                    actions.extend([
                        {'name': 'write_answer', 'args': {'content': content}, 'result': {'written': True}, 'ok': True},
                        {'name': 'read_answer', 'args': {}, 'result': content, 'ok': True},
                    ])
                    rows.append({'case': case_id, 'repeat': repeat, 'arm': arm, 'quality': kw.get('quality', True),
                                 'plan_sha256': plan['plan_sha256'], 'calls': [call_row],
                                 'actions': actions, 'final': 'Done.'})
        return plan, rows

    def prepare(self, **kw):
        plan, rows = self.full_rows(**kw)
        self.write(rows, plan)
        return plan, rows

    def test_missing_row_rejected(self):
        plan, rows = self.prepare()
        (self.out / 'results' / ('%s-1-control.json' % rows[0]['case'])).unlink()
        with self.assertRaises(SystemExit) as caught:
            summarize.load(self.out)
        self.assertIn('incomplete', str(caught.exception))

    def test_duplicate_row_rejected(self):
        plan, rows = self.prepare()
        runner.atomic_write(self.out / 'results' / 'zzz-copy.json', json.dumps(rows[0]))
        with self.assertRaises(SystemExit) as caught:
            summarize.load(self.out)
        self.assertIn('duplicate', str(caught.exception))

    def test_join_and_savings(self):
        report = summarize.summarize(*self.prepare())
        self.assertEqual(report['tokens_total']['control'], 120 * 18)
        for arm in ('skill', 'candidate'):
            stats = report['arms'][arm]
            self.assertGreaterEqual(stats['total_saving_pct'], 10.0)
            self.assertGreater(stats['median_paired_saved_tokens'], 0)
            self.assertEqual(len(stats['per_case']), 6)
        self.assertFalse(report['pass'])  # no external calibration flag

    def test_quality_failure_blocks_gate(self):
        plan, rows = self.prepare()
        for row in rows:
            if row['arm'] == 'candidate':
                for action in row['actions']:
                    if action['name'] == 'write_answer':
                        action['args']['content'] = '[]'
                    if action['name'] == 'read_answer':
                        action['result'] = '[]'
        report = summarize.summarize(plan, rows)
        self.assertFalse(report['gates']['quality_candidate'])
        self.assertFalse(report['pass'])

    def test_calibration_flag_defaults_false(self):
        plan, rows = self.prepare()
        self.assertFalse(summarize.summarize(plan, rows)['gates']['accounting_calibrated'])
        self.assertTrue(summarize.summarize(plan, rows, calibrated=True)['gates']['accounting_calibrated'])

    def test_bootstrap_deterministic(self):
        plan, rows = self.prepare()
        first = summarize.summarize(plan, rows)['arms']['candidate']['ci95_pct']
        second = summarize.summarize(plan, rows)['arms']['candidate']['ci95_pct']
        self.assertEqual(first, second)
        self.assertEqual(summarize.cluster_ci(rows, plan['cases'], 'candidate'), first)

    def test_bootstrap_interval_brackets_and_clusters_by_case(self):
        plan, rows = self.prepare()
        low, high = summarize.cluster_ci(rows, plan['cases'], 'candidate')
        self.assertLessEqual(low, 22.5)
        self.assertGreaterEqual(high, 22.5)
        self.assertLess(low, high)          # case variance must widen the interval
        shuffled = list(rows)
        random.Random(1).shuffle(shuffled)
        self.assertEqual(summarize.cluster_ci(shuffled, plan['cases'], 'candidate'), [low, high])

    def test_low_saving_fails_gate(self):
        plan, rows = self.prepare()
        for row in rows:
            if row['arm'] == 'candidate':
                response = row['calls'][0]['response']
                response['usage'] = {'prompt_tokens': 108, 'completion_tokens': 10, 'total_tokens': 118}
                row['calls'][0]['response_sha256'] = runner.sha(json.dumps(response, sort_keys=True))
        report = summarize.summarize(plan, rows)
        self.assertFalse(report['gates']['saving_candidate'])

    def test_mixed_plan_hash_rejected(self):
        plan, rows = self.prepare()
        rows[0]['plan_sha256'] = '0' * 64
        self.write(rows, plan)
        with self.assertRaises(SystemExit) as caught:
            summarize.load(self.out)
        self.assertIn('another plan', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
