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


Y_AUDIT = ROOT / 'sylver/campaigns/y-2026-10-07/audit.json'

Y_SCRIPT = U_SCRIPT.replace('u-2026-09-27', 'y-2026-10-07')


class YPageTests(unittest.TestCase):
    """docs/y.html shows all 54 obligations of Y={16,28,58}, each covered: 58 answers 28."""

    def test_every_obligation_has_a_row(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('node is not installed')
        out = subprocess.run([node, '-e', Y_SCRIPT, str(ROOT)], capture_output=True, text=True, timeout=60, check=True)
        described = json.loads(out.stdout)
        self.assertEqual((len(described['rows']), described['failures'], described['outcome']), (54, [], 'P'))
        self.assertEqual(described['counts'], {'finite witness': 48, 'certified infinite P-position': 6})
        for row in described['rows']:
            self.assertNotEqual(row['answer'], 'unrecognized evidence', row)
            self.assertTrue(row['link'] and (ROOT / row['link']).exists(), row)

    def test_the_committed_y_audit_is_reproducible(self):
        result = subprocess.run([sys.executable, str(Y_AUDIT.parent / 'audit.py')], capture_output=True, text=True,
                                timeout=900)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        fresh, committed = json.loads(result.stdout), json.loads(Y_AUDIT.read_text())
        self.assertEqual((fresh['outcome'], fresh['failures']), ('P', []))
        self.assertEqual(fresh, committed)
        self.assertEqual(fresh['summary']['by_evidence'], {'finite-witness': 48, 'certified-node': 6})

    def test_a_transcript_that_says_n_is_rejected_even_when_rehashed(self):
        spec = importlib.util.spec_from_file_location('y_audit', Y_AUDIT.parent / 'audit.py')
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        self.assertEqual(audit.finite_witness(9)['evidence'], 'finite-witness')
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(Y_AUDIT.parent / 'y9-certificate.json', tmp)
            shutil.copytree(Y_AUDIT.parent / 'verification/y9', Path(tmp) / 'verification/y9')
            stdout = Path(tmp) / 'verification/y9/native-stdout.txt'
            stdout.write_text(stdout.read_text().replace('P winning_move=none', 'N winning_move=2'))
            receipt = Path(tmp) / 'verification/y9/receipt.json'
            data = json.loads(receipt.read_text())
            data['runs']['native']['stdout_sha256'] = hashlib.sha256(stdout.read_bytes()).hexdigest()
            receipt.write_text(json.dumps(data))
            audit.HERE = Path(tmp)
            self.assertIsNone(audit.finite_witness(9))


Z_AUDIT = ROOT / 'sylver/campaigns/z-2026-10-08/audit.json'

Z_SCRIPT = r'''
const fs = require("fs");
const root = process.argv[process.argv.length - 1];
const { describeAudit } = require(root + "/docs/w.js");
const audit = JSON.parse(fs.readFileSync(root + "/sylver/campaigns/z-2026-10-08/audit.json"));
console.log(JSON.stringify({Z: describeAudit(audit.Z), Zp: describeAudit(audit["Z'"])}));
'''


class ZPageTests(unittest.TestCase):
    """docs/z.html shows all 52 obligations of Z={16,30,56}, each covered: 56 answers 30."""

    def test_every_obligation_has_a_row(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('node is not installed')
        out = subprocess.run([node, '-e', Z_SCRIPT, str(ROOT)], capture_output=True, text=True, timeout=60, check=True)
        described = json.loads(out.stdout)
        for name, total in (('Z', 52), ('Zp', 40)):
            d = described[name]
            self.assertEqual((len(d['rows']), d['failures'], d['outcome']), (total, [], 'P'), name)
            for row in d['rows']:
                self.assertNotEqual(row['answer'], 'unrecognized evidence', row)
                self.assertTrue(row['link'] and (ROOT / row['link']).exists(), row)
        self.assertEqual([r['move'] for r in described['Z']['rows'] if r['evidence'] == 'Z′ is P'], [44])
        self.assertEqual(sorted(r['move'] for r in described['Z']['rows']
                                if r['evidence'] == 'finite witness (native + Kunz)'), [70, 130])

    def test_the_committed_z_audit_is_reproducible(self):
        result = subprocess.run([sys.executable, str(Z_AUDIT.parent / 'audit.py')], capture_output=True, text=True,
                                timeout=900)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        fresh, committed = json.loads(result.stdout), json.loads(Z_AUDIT.read_text())
        self.assertEqual((fresh['outcome'], fresh['failures']), ('P', []))
        self.assertEqual(fresh, committed)
        self.assertEqual(fresh['Z']['obligations']['44']['evidence'], 'z-prime-is-p')

    def test_a_kunz_transcript_with_another_count_is_rejected(self):
        spec = importlib.util.spec_from_file_location('z_audit', Z_AUDIT.parent / 'audit.py')
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        self.assertEqual(audit.finite_witness(audit.Z, 'z', 70)['evidence'], 'finite-witness-native-kunz')
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(Z_AUDIT.parent / 'z70-certificate.json', tmp)
            shutil.copytree(Z_AUDIT.parent / 'verification/z70', Path(tmp) / 'verification/z70')
            shutil.copytree(Z_AUDIT.parent / 'verification/sources', Path(tmp) / 'verification/sources')
            # A fully consistent forgery of the Kunz replay (its stdout, stderr and
            # receipt all say states - 1): only the tie to the native count rejects it.
            receipt = Path(tmp) / 'verification/z70/kunz-receipt.json'
            data = json.loads(receipt.read_text())
            for stream in ('stdout', 'stderr'):
                path = Path(tmp) / f'verification/z70/kunz-{stream}.txt'
                path.write_text(path.read_text().replace(str(data['states']), str(data['states'] - 1)))
                data[f'{stream}_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            data['states'] -= 1
            receipt.write_text(json.dumps(data))
            audit.KUNZ_SNAPSHOT = Path(tmp) / 'verification/sources' / audit.KUNZ_SNAPSHOT.name
            self.assertEqual(audit.kunz_states(Path(tmp) / 'verification/z70', audit.position((*audit.Z, 70, 311)),
                                               data['frobenius']), data['states'])   # the forgery is self-consistent
            audit.HERE = Path(tmp)
            self.assertIsNone(audit.finite_witness(audit.Z, 'z', 70))


O16_AUDIT = ROOT / 'sylver/campaigns/o16-2026-10-09/audit.json'


class OpeningLedgerTests(unittest.TestCase):
    """The ledger of answers to the replies after 16 reproduces, with no failures."""

    def test_the_committed_ledger_is_reproducible(self):
        result = subprocess.run([sys.executable, str(O16_AUDIT.parent / 'audit.py')], capture_output=True, text=True,
                                timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        fresh, committed = json.loads(result.stdout), json.loads(O16_AUDIT.read_text())
        self.assertEqual(fresh, committed)
        self.assertEqual(fresh['failures'], [])
        # Every even reply up to 36 is answered (32 is illegal); 38 is the first open one.
        self.assertEqual([r for r in range(2, 37, 2) if r % 16 and str(r) not in fresh['answers']], [])
        self.assertEqual(fresh['summary']['lowest_unanswered'], 38)

    def test_a_wrong_answer_is_rejected(self):
        spec = importlib.util.spec_from_file_location('o16_audit', O16_AUDIT.parent / 'audit.py')
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        table = {m: (resp, dest) for m, resp, dest in audit.OPENING_16_EVEN_RESPONSES}
        self.assertIsNotNone(audit.check(34, 20, 'certified-node', 'T', table))
        self.assertIsNone(audit.check(34, 22, 'certified-node', 'T', table))     # another position
        self.assertIsNone(audit.check(38, 88, 'campaign', 'u-2026-09-27', table))  # U is {16,26,88}, not {16,38,88}
        self.assertIsNone(audit.check(36, 25, 'finite-witness', None, table))     # o36's certificate has reply 23
        self.assertIsNone(audit.check(62, 37, 'finite-witness', None, table))     # o62 has Kunz, not Python
        self.assertIsNotNone(audit.check(62, 37, 'finite-witness-native-kunz', None, table))
        self.assertIsNone(audit.check(26, 88, 'campaign', 'no-such-campaign', table))

    def test_a_failed_row_counts_as_unanswered(self):
        spec = importlib.util.spec_from_file_location('o16_audit_failed', O16_AUDIT.parent / 'audit.py')
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        audit.ANSWERS = {**audit.ANSWERS, 36: (25, 'finite-witness', None)}
        with io.StringIO() as out, contextlib.redirect_stdout(out):
            self.assertEqual(audit.main(), 1)
            report = json.loads(out.getvalue())
        self.assertEqual(report['summary']['lowest_unanswered'], 36)

    def kunz_replay_copy(self, tmp):
        """A scratch copy of o62's certificate, receipts and pinned Kunz source; its replay directory."""
        shutil.copy(O16_AUDIT.parent / 'o62-certificate.json', tmp)
        shutil.copytree(O16_AUDIT.parent / 'verification/o62', Path(tmp) / 'verification/o62')
        shutil.copytree(O16_AUDIT.parent / 'verification/sources', Path(tmp) / 'verification/sources')
        return Path(tmp) / 'verification/o62'

    def test_a_kunz_replay_that_disagrees_or_is_incomplete_is_rejected(self):
        spec = importlib.util.spec_from_file_location('o16_audit_kunz', O16_AUDIT.parent / 'audit.py')
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        dest = audit.position((16, 62, 37))
        self.assertIsNotNone(audit.finite_witness(62, 37, True))
        with tempfile.TemporaryDirectory() as tmp:
            # A fully consistent forgery of the Kunz replay (its stdout, stderr and
            # receipt all say states - 1): only the tie to the native count rejects it.
            replay = self.kunz_replay_copy(tmp)
            audit.KUNZ_SNAPSHOT = Path(tmp) / 'verification/sources' / audit.KUNZ_SNAPSHOT.name
            receipt = replay / 'kunz-receipt.json'
            data = json.loads(receipt.read_text())
            for stream in ('stdout', 'stderr'):
                path = replay / f'kunz-{stream}.txt'
                path.write_text(path.read_text().replace(str(data['states']), str(data['states'] - 1)))
                data[f'{stream}_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            data['states'] -= 1
            receipt.write_text(json.dumps(data))
            self.assertEqual(audit.kunz_states(replay, dest, data['frobenius']), data['states'])
            audit.HERE = Path(tmp)
            self.assertIsNone(audit.finite_witness(62, 37, True))
        with tempfile.TemporaryDirectory() as tmp:
            # A transcript without the memo check, re-hashed into its receipt.
            replay = self.kunz_replay_copy(tmp)
            audit.KUNZ_SNAPSHOT = Path(tmp) / 'verification/sources' / audit.KUNZ_SNAPSHOT.name
            receipt = replay / 'kunz-receipt.json'
            data = json.loads(receipt.read_text())
            self.assertEqual(audit.kunz_states(replay, dest, data['frobenius']), data['states'])
            stderr = replay / 'kunz-stderr.txt'
            stderr.write_text(''.join(line for line in stderr.read_text().splitlines(keepends=True)
                                      if 'memo verified' not in line))
            data['stderr_sha256'] = hashlib.sha256(stderr.read_bytes()).hexdigest()
            receipt.write_text(json.dumps(data))
            self.assertIsNone(audit.kunz_states(replay, dest, data['frobenius']))
        with tempfile.TemporaryDirectory() as tmp:
            # A source snapshot that no longer matches the pinned hash.
            replay = self.kunz_replay_copy(tmp)
            audit.KUNZ_SNAPSHOT = Path(tmp) / 'verification/sources' / audit.KUNZ_SNAPSHOT.name
            with audit.KUNZ_SNAPSHOT.open('a') as fh:
                fh.write('// edited\n')
            data = json.loads((replay / 'kunz-receipt.json').read_text())
            self.assertIsNone(audit.kunz_states(replay, dest, data['frobenius']))


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
