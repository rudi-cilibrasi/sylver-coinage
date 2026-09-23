"""A legal certificate path is not proof until its finite destination replays."""

import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from sylver.verify_finite_reply import validate_certificate


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "sylver/verify_finite_reply.py"
CERTIFICATE = {
    "schema": 1,
    "parent": [4],
    "opponent_move": 5,
    "reply": 11,
    "destination": [4, 5, 11],
    "destination_outcome": "P",
    "frobenius": 7,
}


class FiniteReplyStructureTests(unittest.TestCase):
    def test_known_paths_and_redundant_parent_generators(self):
        self.assertEqual(validate_certificate(CERTIFICATE), (4, 5, 11))
        terminal = dict(CERTIFICATE, parent=[4], opponent_move=2, reply=3,
                        destination=[2, 3], frobenius=1)
        self.assertEqual(validate_certificate(terminal), (2, 3))
        historical = ROOT / "sylver/campaigns/w-seven-2026-09-22/w134-certificate.json"
        self.assertEqual(validate_certificate(json.loads(historical.read_text())),
                         (16, 26, 62, 85, 98, 134))

    def test_rejects_invalid_paths_and_claims(self):
        replacements = {
            "schema": [None, True, 2],
            "parent": [[], [True], [4, 8], [5, 4], [1], [4.0]],
            "opponent_move": [1, True, 8, 5.0],
            "reply": [1, 5, 9, 11.0],
            "destination": [[4, 5], [4, 6, 11], [4, 5, 11, 15]],
            "destination_outcome": ["N", "unknown", None],
            "frobenius": [True, 7.0, 6, 0],
        }
        for field, values in replacements.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    invalid = copy.deepcopy(CERTIFICATE)
                    invalid[field] = value
                    with self.assertRaises(ValueError):
                        validate_certificate(invalid)
        with self.assertRaises(ValueError):
            validate_certificate(dict(CERTIFICATE, parent=[8], opponent_move=10,
                                      reply=12, destination=[8, 10, 12]))


@unittest.skipUnless(shutil.which("g++"), "requires g++")
class FiniteReplyReplayTests(unittest.TestCase):
    def run_verifier(self, directory, certificate, *extra):
        path = directory / "certificate.json"
        path.write_text(json.dumps(certificate))
        output = directory / "replay"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--certificate", str(path),
             "--output", str(output), *extra],
            cwd=directory, text=True, capture_output=True, timeout=30,
        )
        return result, output

    def test_fresh_native_and_python_replays_outside_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            result, output = self.run_verifier(directory, CERTIFICATE, "--python")
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertEqual(receipt["status"], "verified")
            for name in ("native", "python"):
                self.assertEqual(receipt["runs"][name]["states"], 5)
                self.assertEqual(receipt["runs"][name]["outcome"], "P")
            before = (output / "receipt.json").read_bytes()
            rerun, _ = self.run_verifier(directory, CERTIFICATE)
            self.assertNotEqual(rerun.returncode, 0)
            self.assertEqual((output / "receipt.json").read_bytes(), before)

    def test_legal_path_to_n_is_rejected_with_incomplete_receipt(self):
        # This passes the structural check but its destination is N via 6.
        false_claim = dict(CERTIFICATE, reply=7, destination=[4, 5, 7], frobenius=6)
        with tempfile.TemporaryDirectory() as tmp:
            result, output = self.run_verifier(Path(tmp), false_claim)
            self.assertNotEqual(result.returncode, 0)
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertEqual(receipt["status"], "incomplete")
            self.assertTrue((output / "native-stdout.txt").read_text().startswith("N "))

    def test_timeout_retains_receipt_and_transcript(self):
        historical = ROOT / "sylver/campaigns/w-seven-2026-09-22/w134-certificate.json"
        with tempfile.TemporaryDirectory() as tmp:
            result, output = self.run_verifier(
                Path(tmp), json.loads(historical.read_text()), "--seconds", "1e-12")
            self.assertNotEqual(result.returncode, 0)
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertEqual(receipt["status"], "incomplete")
            self.assertTrue(receipt["runs"]["native"]["timed_out"])


if __name__ == "__main__":
    unittest.main()
