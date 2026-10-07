import hashlib
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'sylver/campaigns/w-p-2026-09-27/audit.json'

SCRIPT = r'''
const fs = require("fs");
const root = process.argv[process.argv.length - 1];
const { checkLabel, describeAudit } = require(root + "/docs/w.js");
const audit = JSON.parse(fs.readFileSync(root + "/sylver/campaigns/w-p-2026-09-27/audit.json"));
const labels = [checkLabel({ valid: true, outcome: "N" }), checkLabel({ valid: false, error: "state limit exceeded — use the native solver" }),
                checkLabel({ valid: false, error: "leaf {1,2} is N, not P" }), checkLabel({ valid: true, outcome: "P" })];
console.log(JSON.stringify({ described: describeAudit(audit), labels: labels.map((l) => l.cls) }));
'''


class WPageTests(unittest.TestCase):
    """docs/w.js must describe every obligation in the campaign audit and link
    each answer to a file in the repository."""

    def test_every_obligation_has_a_row_and_evidence(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('node is not installed')
        audit = json.loads(AUDIT.read_text())
        out = subprocess.run([node, '-e', SCRIPT, str(ROOT)], capture_output=True, text=True, timeout=60, check=True)
        report = json.loads(out.stdout)
        described = report['described']
        self.assertEqual(described['outcome'], 'P')
        self.assertEqual(described['failures'], [])
        self.assertEqual([r['move'] for r in described['rows']], sorted(int(m) for m in audit['obligations']))
        self.assertEqual(len(described['rows']), audit['summary']['obligations'])
        for row in described['rows']:
            self.assertNotEqual(row['answer'], 'unrecognized evidence', row)
            self.assertTrue(row['link'] and (ROOT / row['link']).exists(), row)
            self.assertEqual(row['checkable'], row['evidence'] == 'Book certificate', row)
        self.assertEqual(report['labels'], ['ok', 'muted', 'bad', 'bad'])

    def test_the_committed_audit_is_reproducible(self):
        # audit.py re-derives the obligations and re-checks every certificate,
        # receipt and transcript; its output must equal the committed file
        # (regenerate audit.json whenever The Book changes).
        result = subprocess.run([sys.executable, str(AUDIT.parent / 'audit.py')], capture_output=True, text=True,
                                timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        fresh, committed = json.loads(result.stdout), json.loads(AUDIT.read_text())
        self.assertEqual((fresh['outcome'], fresh['failures']), ('P', []))
        self.assertEqual(fresh, committed)   # the audit is deterministic for a given Book
        nodes = sorted(int(m) for m, row in fresh['obligations'].items() if row['evidence'] == 'certified-node')
        self.assertEqual(nodes, [12, 36])



U_AUDIT = ROOT / 'sylver/campaigns/u-2026-09-27/audit.json'

U_SCRIPT = r'''
const fs = require("fs");
const root = process.argv[process.argv.length - 1];
const { describeAudit } = require(root + "/docs/w.js");
const audit = JSON.parse(fs.readFileSync(root + "/sylver/campaigns/u-2026-09-27/audit.json"));
console.log(JSON.stringify(describeAudit(audit)));
'''


class UPageTests(unittest.TestCase):
    """docs/u.html shows all 59 obligations of U, each covered; move 82 by X's own audit."""

    def test_every_obligation_has_a_row(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('node is not installed')
        out = subprocess.run([node, '-e', U_SCRIPT, str(ROOT)], capture_output=True, text=True, timeout=60, check=True)
        described = json.loads(out.stdout)
        self.assertEqual(len(described['rows']), 59)
        self.assertEqual(described['failures'], [])
        self.assertEqual(described['outcome'], 'P')
        self.assertEqual([r['move'] for r in described['rows'] if r['evidence'] == 'open'], [])
        self.assertEqual([r['move'] for r in described['rows'] if r['evidence'] == 'X is N'], [82])
        for row in described['rows']:
            self.assertNotEqual(row['answer'], 'unrecognized evidence', row)
            self.assertTrue(row['link'] and (ROOT / row['link']).exists(), row)

    def test_the_committed_u_audit_is_reproducible(self):
        result = subprocess.run([sys.executable, str(U_AUDIT.parent / 'audit.py')], capture_output=True, text=True,
                                timeout=900)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        fresh, committed = json.loads(result.stdout), json.loads(U_AUDIT.read_text())
        self.assertEqual((fresh['outcome'], fresh['failures']), ('P', []))
        self.assertEqual(fresh, committed)
        self.assertEqual(fresh['summary']['covered'], 59)
        self.assertEqual({k: fresh['obligations']['82'][k] for k in ('evidence', 'reply', 'destination')},
                         {'evidence': 'x-is-n', 'reply': 701, 'destination': '16,26,82,88,701'})


X_AUDIT = ROOT / 'sylver/campaigns/x-2026-10-06/audit.json'


class XAuditTests(unittest.TestCase):
    """X={16,26,82,88} is N: {16,26,82,88,701} is P by two sequential replays that agree."""

    def test_the_committed_x_audit_is_reproducible(self):
        result = subprocess.run([sys.executable, str(X_AUDIT.parent / 'audit.py')], capture_output=True, text=True,
                                timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        fresh, committed = json.loads(result.stdout), json.loads(X_AUDIT.read_text())
        self.assertEqual(fresh, committed)
        self.assertEqual((fresh['outcome'], fresh['destination'], fresh['destination_outcome']),
                         ('N', '16,26,82,88,701', 'P'))
        self.assertEqual(sorted(fresh['replays']), ['bitset', 'kunz'])
        self.assertEqual(len({run['states'] for run in fresh['replays'].values()}), 1)
        self.assertTrue(fresh['odd_replies_below_701']['all_N'])
        self.assertEqual(fresh['sweep']['P_reply'], 701)

    def load(self, name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_altered_replays_are_rejected(self):
        audit = self.load('x_audit', X_AUDIT.parent / 'audit.py')
        destination = audit.position((*audit.X, audit.REPLY))
        original = json.loads(audit.RECEIPT.read_text())
        evidence = audit.RECEIPT.parent

        def failures_with(edit_receipt=None, edit_files=None):
            receipt = json.loads(json.dumps(original))
            if edit_receipt:
                edit_receipt(receipt)
            with tempfile.TemporaryDirectory() as tmp:
                shutil.copytree(evidence, tmp, dirs_exist_ok=True)
                if edit_files:
                    edit_files(Path(tmp), receipt)
                (Path(tmp) / 'receipt.json').write_text(json.dumps(receipt))
                audit.RECEIPT = Path(tmp) / 'receipt.json'
                failures = []
                audit.replays(destination, 819, failures)
                return failures

        def rewrite(name, stream, transform):   # edit a transcript and re-hash it into the receipt
            def edit(directory, receipt):
                path = directory / f'{name}-{stream}.txt'
                path.write_text(transform(path.read_text()))
                receipt['runs'][name][f'{stream}_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            return edit

        rejected = 'the {} replay is not a verified sequential P result for 16,26,82,88,701'
        self.assertEqual(failures_with(), [])
        # A transcript changed after the receipt was written.
        self.assertIn('the bitset transcripts do not match the receipt', failures_with(
            edit_files=lambda d, r: (d / 'bitset-stdout.txt').write_text('N winning_move=2 frobenius=819 states=1\n')))
        # Consistent records of a different count: the replays must agree.
        states = original['runs']['bitset']['states']

        def lower(directory, receipt):
            receipt['runs']['bitset']['states'] = states - 1
            for stream in ('stdout', 'stderr'):
                rewrite('bitset', stream, lambda t: t.replace(str(states), str(states - 1)))(directory, receipt)
        self.assertEqual(failures_with(edit_files=lower), ['the sequential replays disagree on the state count'])
        # An N outcome, re-hashed.
        self.assertIn(rejected.format('kunz'), failures_with(
            edit_files=rewrite('kunz', 'stdout', lambda t: t.replace('P winning_move=none', 'N winning_move=2'))))
        # A threaded search, re-hashed, whatever the receipt's own command says.
        self.assertIn(rejected.format('kunz'), failures_with(
            edit_files=rewrite('kunz', 'stderr', lambda t: t.replace('--threads 1 ', '--threads 10 '))))
        # Extra lines in a re-hashed stderr: a second command, a failed exit, a failed check.
        for extra in ('\tCommand being timed:"x --threads 10"\n', '\tExit status: 1\n',
                      'kunz_solver: memo verification failed: a P entry has a move to a child\n'):
            self.assertIn(rejected.format('kunz'), failures_with(
                edit_files=rewrite('kunz', 'stderr', lambda t, e=extra: t + e)), extra)
        # A command without --verify-memo, consistent in the receipt and the transcript.
        def drop_verify(directory, receipt):
            receipt['runs']['bitset']['command'].remove('--verify-memo')
            rewrite('bitset', 'stderr', lambda t: t.replace(' --verify-memo', ''))(directory, receipt)
        self.assertIn(rejected.format('bitset'), failures_with(edit_files=drop_verify))
        # The bitset build without its Kunz-key flag; another position; a changed source.
        self.assertIn(rejected.format('bitset'), failures_with(
            lambda r: r['runs']['bitset'].update(build=r['runs']['bitset']['build'].replace(' -DSYLVER_PARALLEL_KUNZ_KEYS', ''))))
        self.assertIn('the receipt is for another position', failures_with(lambda r: r.update(position=[16, 26, 82, 88, 703])))
        self.assertIn('the kunz source snapshot does not match the receipt', failures_with(
            edit_files=lambda d, r: (d / r['runs']['kunz']['source_snapshot']).write_text('// edited\n')))

    def test_a_p_reply_below_701_clears_only_the_least_reply_verdict(self):
        audit = self.load('x_audit_sweep', X_AUDIT.parent / 'audit.py')
        rows = [json.loads(line) for line in audit.LEDGER.read_text().splitlines()]
        with tempfile.TemporaryDirectory() as tmp:
            for row in rows:
                if row['r'] == 695:
                    row.update(outcome='P', winning_move=None)
            ledger = Path(tmp) / 'ledger.jsonl'
            ledger.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            audit.LEDGER = ledger
            failures = []
            below = audit.odd_replies_below(failures)
            self.assertEqual((below['all_N'], below['P_replies'], failures), (False, [695], []))
            # The whole audit: X is still N, but 701 is no longer reported least.
            with io.StringIO() as out, contextlib.redirect_stdout(out):
                self.assertEqual(audit.main(), 0)
                report = json.loads(out.getvalue())
            self.assertEqual((report['outcome'], report['least_winning_odd_reply']), ('N', None))
            sweep = audit.sweep(failures)
            self.assertEqual(sweep['P_reply'], 701)
            # A sweep whose last row is not the P row for 701 fails.
            ledger.write_text(''.join(json.dumps(row) + '\n' for row in rows[:-1]))
            failures = []
            audit.sweep(failures)
            self.assertIn('the sweep does not end with the P row for 701', failures)

    def test_the_u_audit_rejects_a_failing_x_audit(self):
        u_audit = self.load('u_audit', U_AUDIT.parent / 'audit.py')
        good = json.loads(X_AUDIT.read_text())
        self.assertEqual(u_audit.x_is_n(82, good)['evidence'], 'x-is-n')
        for broken in ({**good, 'failures': ['something']}, {**good, 'outcome': 'unknown'},
                       {**good, 'destination': '16,26,82,88,703'}, {**good, 'destination_outcome': None}, {}):
            self.assertIsNone(u_audit.x_is_n(82, broken))
        self.assertIsNone(u_audit.x_is_n(98, good))


if __name__ == '__main__':
    unittest.main()
