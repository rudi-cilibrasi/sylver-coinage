import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = r'''
const fs = require("fs");
const root = process.argv[process.argv.length - 1];
const { SylverSolver } = require(root + "/docs/solver.js");
const { checkCertificate, largestLeaf } = require(root + "/docs/book.js");
const solve = (gens) => (new SylverSolver(gens, 8000000).solve().winningMove === null ? "P" : "N");
const index = JSON.parse(fs.readFileSync(root + "/sylver/arena/book/index.json"));
const results = [];
for (const [target, t] of Object.entries(index.targets)) {
  for (const e of t.entries) {
    const proof = JSON.parse(fs.readFileSync(root + "/sylver/arena/book/certificates/" + e.certificate + ".json"));
    if (e.states > 500000) continue;   // keep the test quick; the page itself allows larger
    const r = checkCertificate(proof, solve);
    results.push({ target, expected: t.outcome, valid: r.valid, outcome: r.outcome, error: r.error });
  }
}
const good = { schema: 1, root: "4,6", nodes: {
  "4,6": { rule: "cover", outcome: "P", tail: "quiet-end-v1", children: [{ move: 2, child: "2" }] },
  "2": { rule: "edge", outcome: "N", move: 3, child: "2,3" }, "2,3": { rule: "finite", outcome: "P" } } };
const tamper = (f) => { const p = JSON.parse(JSON.stringify(good)); f(p); return checkCertificate(p, solve).valid; };
const controls = {
  good: checkCertificate(good, solve).valid,
  wrongLeaf: tamper((p) => { p.nodes["2,3"].outcome = "N"; }),
  illegalMove: tamper((p) => { p.nodes["2"].move = 4; }),
  incompleteCover: tamper((p) => { p.nodes["4,6"].children = []; }),
  circular: tamper((p) => { p.nodes["2"] = { rule: "edge", outcome: "N", move: 3, child: "2" }; }),
};
console.log(JSON.stringify({ results, controls }));
'''


class BookPageCheckerTests(unittest.TestCase):
    """docs/book.js is an independent JavaScript implementation of the
    referee's rules; it must accept the Book's certificates and reject
    tampered ones."""

    def test_javascript_checker_agrees_with_the_book(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('node is not installed')
        out = subprocess.run([node, '-e', SCRIPT, str(ROOT)], capture_output=True, text=True, timeout=600, check=True)
        report = json.loads(out.stdout)
        self.assertGreaterEqual(len(report["results"]), 4)
        for row in report['results']:
            self.assertTrue(row['valid'], row)
            self.assertEqual(row['outcome'], row['expected'], row)
        self.assertEqual(report['controls'], {'good': True, 'wrongLeaf': False, 'illegalMove': False,
                                              'incompleteCover': False, 'circular': False})
