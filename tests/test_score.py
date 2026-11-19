import csv
import io
import unittest
from score import score

HEADER = 'case,repeat,arm,tokens,quality\n'
GOOD = 'demo,1,control,110,pass\ndemo,1,jeda,100,pass\n'

def run(rows):
    return score(csv.DictReader(io.StringIO(HEADER + rows)), ['demo'], 1)

class ScoreTests(unittest.TestCase):
    def test_saving(self):
        self.assertEqual(run(GOOD)['saved_tokens'], 10)

    def test_quality_blocks_saving(self):
        self.assertFalse(run(GOOD.replace('100,pass', '100,fail'))['eligible'])

    def test_equal_cost_not_saving(self):
        self.assertFalse(run(GOOD.replace('110', '100'))['eligible'])

    def test_invalid_inputs(self):
        for rows in ('', GOOD + GOOD, GOOD.splitlines(True)[0], GOOD.replace('100', '-1'), GOOD.replace('pass', '?'), GOOD.replace('demo', 'extra'), GOOD.replace('jeda', 'typo'), GOOD.replace('110', '0'), GOOD.replace('demo,1,jeda','demo,2,jeda')):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                run(rows)
