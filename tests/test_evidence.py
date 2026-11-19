import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EvidenceTests(unittest.TestCase):
    def test_exported_hashes(self):
        base = ROOT / 'evidence'
        manifest = json.loads((base / 'SHA256SUMS.json').read_text())
        for name, expected in manifest.items():
            with self.subTest(file=name):
                path = (base / name).resolve()
                self.assertTrue(path.is_relative_to(base.resolve()))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_runtime_matches_trial(self):
        skill = (ROOT / 'SKILL.md').read_bytes()
        self.assertEqual(skill, (ROOT / 'evidence/tested-SKILL.md').read_bytes())
        plan = json.loads((ROOT / 'evidence/corrected/plan.json').read_text())
        self.assertEqual(hashlib.sha256(skill).hexdigest(), plan['skill_sha256'])
