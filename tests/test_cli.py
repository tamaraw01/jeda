import pathlib
import subprocess
import sys
import tempfile
import unittest


class CsvHeaderTests(unittest.TestCase):
    def test_duplicate_quality_header_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / 'cases.json').write_text('["a"]', encoding='utf-8')
            (root / 'input.csv').write_text('case,repeat,arm,tokens,quality,quality\na,1,control,20,fail,pass\na,1,jeda,10,fail,pass\n', encoding='utf-8')
            script = pathlib.Path(__file__).resolve().parents[1] / 'score.py'
            result = subprocess.run([sys.executable, str(script), str(root / 'input.csv'), '--cases', str(root / 'cases.json'), '--repeats', '1'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('exactly once', result.stderr)
