import contextlib
import hashlib
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
C72 = ROOT / 'sylver/campaigns/c72-2026-10-18'
SCAN = ROOT / 'sylver/campaigns/r38-2026-10-09/scan'
SEARCH_ONLY = [68, 78, 84, 100, 106, 116, 132, 154]    # the long children of 72 that the hunt settled


def load(name):
    spec = importlib.util.spec_from_file_location(name, C72 / 'audit.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    return audit


def scratch(audit, tmp, *names):
    """Copy these certificates and their replays into tmp/c72 and point the audit there."""
    here = Path(tmp) / 'c72'
    (here / 'verification').mkdir(parents=True)
    for name in names:
        shutil.copy(C72 / f'{name}-certificate.json', here)
        shutil.copytree(C72 / 'verification' / name, here / 'verification' / name, ignore=shutil.ignore_patterns('build'))
    audit.HERE, audit.ROOT = here, Path(tmp)
    return here


class C72AuditTests(unittest.TestCase):
    """Every obligation of {16,38,72} but the hunt's eight is certified N; those eight rest on search."""

    def test_the_committed_audit_is_reproducible(self):
        result = subprocess.run([sys.executable, str(C72 / 'audit.py')], capture_output=True, text=True, timeout=900)
        fresh, committed = json.loads(result.stdout), json.loads((C72 / 'audit.json').read_text())
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        self.assertEqual(fresh, committed)
        self.assertEqual((fresh['failures'], fresh['search_only'], fresh['outcome']), ([], SEARCH_ONLY, 'unknown'))
        self.assertEqual(fresh['summary']['certified'], 60)
        self.assertEqual(len(fresh['obligations']), 68)

    def test_routes_are_the_reply_38_logs(self):
        audit = load('c72_routes')
        logged = {}
        for line in (SCAN / 'odd72_all.out').read_text().splitlines():
            m = re.match(r'move=(\d+) N winning_move=(\d+) ', line)
            logged[int(m[1])] = int(m[2])
        for row in map(json.loads, (SCAN / 'even_72.jsonl').read_text().splitlines()):
            if row['status'] == 'resolved':
                logged[row['e']] = row['reply']
        for e in (58, 66):
            rows = map(json.loads, (SCAN / f'deep_16-38-{e}-72.jsonl').read_text().splitlines())
            logged[e] = int(next(r['P'] for r in rows if r.get('P')))
        logged[56] = 60                       # {16,38,72,56} = {16,38,56}, which 60 takes to B56
        for row in map(json.loads, (SCAN / 'hunt.jsonl').read_text().splitlines()):
            if row['outcome'] == 'P':
                logged[next(x for x in row['child'] if x not in (16, 38, 72))] = row['w']
        self.assertEqual(audit.ROUTES, logged)

    def test_a_shared_destination_must_be_reached(self):
        audit = load('c72_shared')
        certs = audit.certificates()
        self.assertEqual(audit.finite_witness(3, 2, certs)['certificate'], str((C72 / 'c72_3-certificate.json')
                                                                               .relative_to(ROOT)))
        self.assertIsNotNone(audit.finite_witness(2, 3, certs))       # 2 then 3 also reaches {2,3}
        self.assertIsNone(audit.finite_witness(3, 4, certs))          # {16,38,72,3,4} has no certificate

    def test_a_transcript_that_says_n_is_rejected_even_when_rehashed(self):
        audit = load('c72_transcript')
        with tempfile.TemporaryDirectory() as tmp:
            here = scratch(audit, tmp, 'c72_5')
            self.assertIsNotNone(audit.finite_witness(5, 18, audit.certificates()))   # the copy as it is passes
            stdout = here / 'verification/c72_5/native-stdout.txt'
            stdout.write_text(stdout.read_text().replace('P winning_move=none', 'N winning_move=2'))
            receipt = here / 'verification/c72_5/receipt.json'
            data = json.loads(receipt.read_text())
            data['runs']['native']['stdout_sha256'] = hashlib.sha256(stdout.read_bytes()).hexdigest()
            receipt.write_text(json.dumps(data))
            self.assertIsNone(audit.finite_witness(5, 18, audit.certificates()))

    def test_a_python_count_that_differs_is_rejected(self):
        audit = load('c72_counts')
        with tempfile.TemporaryDirectory() as tmp:
            here = scratch(audit, tmp, 'c72_5')
            receipt = here / 'verification/c72_5/receipt.json'
            data = json.loads(receipt.read_text())
            data['runs']['python']['states'] += 1
            receipt.write_text(json.dumps(data))
            self.assertIsNone(audit.finite_witness(5, 18, audit.certificates()))

    def test_the_large_witnesses_need_their_kunz_replays(self):
        audit = load('c72_kunz')
        certs = audit.certificates()
        for m, v in ((58, 129), (170, 71)):
            self.assertEqual(audit.finite_witness(m, v, certs)['evidence'], 'finite-witness-native-kunz', m)
        audit.NATIVE_KUNZ = set()            # without the exception a Python replay is required
        self.assertIsNone(audit.finite_witness(58, 129, certs))
        audit = load('c72_kunz_missing')
        with tempfile.TemporaryDirectory() as tmp:
            here = scratch(audit, tmp, 'c72_58')
            (here / 'verification/c72_58/kunz-receipt.json').unlink()   # the native replay alone is not enough
            self.assertIsNone(audit.finite_witness(58, 129, audit.certificates()))

    def test_an_illegal_listed_reply_is_a_failure(self):
        audit = load('c72_illegal')
        audit.ROUTES = {**audit.ROUTES, 9: 18}     # 18 is generated in {16,38,72,9}, so it is no move there
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(audit.main(), 1)
        self.assertIn('move 9: no legal listed reply', json.loads(out.getvalue())['failures'])

    def test_a_position_the_reply_38_audit_does_not_find_p_is_not_certified(self):
        audit = load('c72_positions')
        self.assertEqual(audit.certified_position(56, 60, {'B56': 'P'})['section'], 'B56')
        self.assertIsNone(audit.certified_position(56, 60, {'B56': 'unknown'}))
        self.assertIsNone(audit.certified_position(24, 40, {'B24': 'P', 'B28': 'P'}))   # 40 does not reach B24

    def test_the_docs_give_the_audited_count(self):
        certified = json.loads((C72 / 'audit.json').read_text())['summary']['certified']
        for path in ('README.md', 'docs/index.html', 'docs/mint.js'):
            self.assertRegex((ROOT / path).read_text(), rf'\b{certified} of (the|its) 68 obligations', path)

    def test_search_witnesses_are_not_certified(self):
        report = json.loads((C72 / 'audit.json').read_text())
        for m in SEARCH_ONLY:
            row = report['obligations'][str(m)]
            self.assertEqual(row['evidence'], 'search-witness', m)
        nodes = {row['certificate'].split()[1] for row in report['obligations'].values()
                 if row['evidence'] == 'certified-node'}
        self.assertEqual(nodes, {'C', 'E', 'F', 'P0'})   # none needs Sicherman's {8,10,22}


if __name__ == '__main__':
    unittest.main()
