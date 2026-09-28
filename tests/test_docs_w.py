import json
import shutil
import subprocess
import sys
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
        # receipt and transcript. Its verdict must match the committed file:
        # outcome P, every obligation covered, certified nodes exactly for 12
        # and 36, and the same evidence wherever the committed file has Book
        # evidence. A finite witness may since have entered The Book, which
        # the audit prefers.
        result = subprocess.run([sys.executable, str(AUDIT.parent / 'audit.py')], capture_output=True, text=True,
                                timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        fresh, committed = json.loads(result.stdout), json.loads(AUDIT.read_text())
        self.assertEqual((fresh['outcome'], fresh['failures']), ('P', []))
        self.assertEqual(sorted(fresh['obligations']), sorted(committed['obligations']))
        for m, row in committed['obligations'].items():
            if row['evidence'] == 'finite-witness':
                self.assertIn(fresh['obligations'][m]['evidence'], ('finite-witness', 'book'), m)
            else:
                self.assertEqual(fresh['obligations'][m], row, m)
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
    """docs/u.html shows all 59 obligations of U, with X (move 82) the only open one."""

    def test_every_obligation_has_a_row(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('node is not installed')
        out = subprocess.run([node, '-e', U_SCRIPT, str(ROOT)], capture_output=True, text=True, timeout=60, check=True)
        described = json.loads(out.stdout)
        self.assertEqual(len(described['rows']), 59)
        self.assertEqual(described['failures'], [])
        self.assertEqual([r['move'] for r in described['rows'] if r['evidence'] == 'open'], [82])
        for row in described['rows']:
            self.assertNotEqual(row['answer'], 'unrecognized evidence', row)
            if row['evidence'] != 'open':
                self.assertTrue(row['link'] and (ROOT / row['link']).exists(), row)

    def test_the_committed_u_audit_is_reproducible(self):
        result = subprocess.run([sys.executable, str(U_AUDIT.parent / 'audit.py')], capture_output=True, text=True,
                                timeout=900)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        fresh, committed = json.loads(result.stdout), json.loads(U_AUDIT.read_text())
        self.assertEqual((fresh['outcome'], fresh['failures']), ('P if and only if X is N', []))
        self.assertEqual({m: r['evidence'] for m, r in fresh['obligations'].items()},
                         {m: r['evidence'] for m, r in committed['obligations'].items()})
        self.assertEqual(fresh['open'], committed['open'])
        self.assertEqual(sorted(int(m) for m in fresh['open']), [82])
        self.assertEqual(fresh['open']['82']['P_replies'], [])


if __name__ == '__main__':
    unittest.main()
