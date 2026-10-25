import contextlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R40 = ROOT / 'sylver/campaigns/r40-2026-10-23'
B78 = (16, 36, 40, 78)
WORDS = {26: 'twenty-six'}


def load(name):
    spec = importlib.util.spec_from_file_location(name, R40 / 'audit.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    return audit


def scratch(audit, tmp, *names):
    """Copy these certificates and their replays into tmp/r40 and point the audit there."""
    here = Path(tmp) / 'r40'
    (here / 'verification').mkdir(parents=True)
    for name in names:
        shutil.copy(R40 / f'{name}-certificate.json', here)
        shutil.copytree(R40 / 'verification' / name, here / 'verification' / name, ignore=shutil.ignore_patterns('build'))
    (Path(tmp) / 'r38-2026-10-09').symlink_to(R40.parent / 'r38-2026-10-09')   # where a Kunz receipt's pinned source is
    audit.HERE, audit.ROOT = here, Path(tmp)
    return here


class R40AuditTests(unittest.TestCase):
    """Q, B58 and B78 are certified P, and with them twenty-six answers to the reply 40 fail."""

    def test_the_committed_audit_is_reproducible(self):
        result = subprocess.run([sys.executable, str(R40 / 'audit.py')], capture_output=True, text=True, timeout=900)
        fresh, committed = json.loads(result.stdout), json.loads((R40 / 'audit.json').read_text())
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        self.assertEqual(fresh, committed)
        self.assertEqual((fresh['verdict'], fresh['failures']), ('verified', []))
        self.assertEqual({name: fresh[name]['outcome'] for name in ('Q', 'B58', 'B78', 'B28', "Z'")},
                         dict.fromkeys(('Q', 'B58', 'B78', 'B28', "Z'"), 'P'))
        self.assertEqual(fresh['B78']['summary']['by_evidence'],
                         {'finite-witness': 50, 'finite-witness-native-kunz': 3, 'certified-node': 7, 'nested-p': 1})
        refuted = fresh['refuted_answers_to_40']
        self.assertEqual(len(refuted), 26)
        self.assertEqual({row['outcome'] for row in refuted.values()}, {'N'})

    def test_the_large_witnesses_need_their_kunz_replays(self):
        audit = load('r40_kunz')
        p = audit.position(B78)
        for m in (86, 90, 102):
            self.assertEqual(audit.finite_witness(p, 'b78_', m)['evidence'], 'finite-witness-native-kunz', m)
        audit.NATIVE_KUNZ = {}               # without the exception a Python replay is required
        self.assertIsNone(audit.finite_witness(p, 'b78_', 90))
        for change in ('unlink', 'count'):
            audit = load(f'r40_kunz_{change}')
            with tempfile.TemporaryDirectory() as tmp:
                here = scratch(audit, tmp, 'b78_90')
                self.assertIsNotNone(audit.finite_witness(p, 'b78_', 90))   # the copy as it is passes
                receipt = here / 'verification/b78_90/kunz-receipt.json'
                if change == 'unlink':       # the native replay alone is not enough
                    receipt.unlink()
                else:                        # nor is a Kunz count other than the native one
                    data = json.loads(receipt.read_text())
                    data['states'] += 1
                    receipt.write_text(json.dumps(data))
                self.assertIsNone(audit.finite_witness(p, 'b78_', 90), change)

    def test_a_python_witness_cannot_pass_as_a_kunz_one(self):
        audit = load('r40_python')
        p = audit.position(B78)
        self.assertEqual(audit.finite_witness(p, 'b78_', 122)['evidence'], 'finite-witness')
        audit.NATIVE_KUNZ = {'b78_': {122}}
        self.assertIsNone(audit.finite_witness(p, 'b78_', 122))

    def test_a_python_count_that_differs_is_rejected(self):
        audit = load('r40_counts')
        p = audit.position(B78)
        with tempfile.TemporaryDirectory() as tmp:
            here = scratch(audit, tmp, 'b78_5')
            self.assertIsNotNone(audit.finite_witness(p, 'b78_', 5))   # the copy as it is passes
            receipt = here / 'verification/b78_5/receipt.json'
            data = json.loads(receipt.read_text())
            data['runs']['python']['states'] += 1
            receipt.write_text(json.dumps(data))
            self.assertIsNone(audit.finite_witness(p, 'b78_', 5))

    def test_a_nested_route_needs_a_position_found_p_before(self):
        audit = load('r40_nested')
        p, routes = audit.position(B78), audit.POSITIONS['B78'][2]
        q = (audit.position((16, 20, 46)), True)
        self.assertEqual(audit.nested_p(p, routes, 20, {'Q': q})['section'], 'Q')
        self.assertIsNone(audit.nested_p(p, routes, 20, {}))                            # Q not audited yet
        self.assertIsNone(audit.nested_p(p, routes, 20, {'Q': (q[0], False)}))          # Q not found P
        self.assertIsNone(audit.nested_p(p, routes, 20, {'Q': ((16, 20, 48), True)}))   # 46 does not reach that
        self.assertIsNone(audit.nested_p(p, routes, 22, {'Q': q}))                      # 22's route is the node P0

    def test_b78_fails_if_audited_before_q(self):
        audit = load('r40_order')
        audit.POSITIONS = {'B78': audit.POSITIONS['B78'], 'Q': audit.POSITIONS['Q']}
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(audit.main(), 1)
        report = json.loads(out.getvalue())
        self.assertEqual((report['Q']['outcome'], report['B78']['outcome']), ('P', 'unknown'))
        self.assertIn('B78: move 20 has no accepted evidence', report['failures'])

    def test_the_docs_give_the_audited_refutations(self):
        audit = load('r40_docs')
        text = (R40 / 'RESULT.md').read_text()
        table = {int(a): int(m) for a, m in re.findall(r'^\| (\d+) \| \{[\d,]+\} \| (\d+) \|', text, re.M)}
        self.assertEqual(table, {a: move for a, (move, _) in audit.REFUTED.items()})
        count = len(audit.REFUTED)
        self.assertIn(f'the audit refutes {WORDS[count]} answers to 40', text)
        self.assertRegex((R40.parent / 'o16-2026-10-09/RESULT.md').read_text(), rf'refutes\s+{count} answers')


if __name__ == '__main__':
    unittest.main()
