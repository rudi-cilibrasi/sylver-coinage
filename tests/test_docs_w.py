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
        # receipt and transcript; its verdict must match the committed file.
        result = subprocess.run([sys.executable, str(AUDIT.parent / 'audit.py')], capture_output=True, text=True,
                                timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        self.assertEqual(json.loads(result.stdout), json.loads(AUDIT.read_text()))
        audit = json.loads(result.stdout)
        nodes = sorted(int(m) for m, row in audit['obligations'].items() if row['evidence'] == 'certified-node')
        self.assertEqual(nodes, [12, 36])


if __name__ == '__main__':
    unittest.main()
