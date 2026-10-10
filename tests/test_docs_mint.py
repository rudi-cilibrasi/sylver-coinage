import json
import shutil
import subprocess
import unittest
from math import gcd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'sylver/campaigns/o16-2026-10-09/audit.json'
R38 = ROOT / 'sylver/campaigns/r38-2026-10-09/audit.json'

# Export the Mint's data, and solve the small finite destinations of its
# answer table with the page's own evaluator (solver.js).
SCRIPT = r'''
const root = process.argv[process.argv.length - 1];
const mint = require(root + "/docs/mint.js");
const { SylverSolver } = require(root + "/docs/solver.js");
const solved = {};
for (const [reply, answer, , , finite] of mint.TABLE) {
  if (!finite) continue;
  const s = new SylverSolver(finite, 200000);
  try { solved[reply] = { move: s.winningMove(s.initialState), states: s.memo.size }; }
  catch (e) { solved[reply] = { error: String(e) }; }
}
// Blok's mirror: play random games from {8, 12}; after each move the mate
// must be unpaid, and the unpaid amounts must be 1 and whole pairs.
const mirror = { games: 0, moves: 0, failures: [] };
let seed = 7;
const random = (n) => { seed = (seed * 48271) % 2147483647; return seed % n; };  // MINSTD, exact in doubles
for (let game = 0; game < 300; game++) {
  const named = [8, 12];
  for (let turn = 0; turn < 60; turn++) {
    const paid = mint.paidUpTo(named, 260);
    const live = []; for (let n = 2; n <= 200; n++) if (!paid[n]) live.push(n);
    if (!live.length) break;
    for (const n of live) if (mint.mirrorMate(n) <= 256 && paid[mint.mirrorMate(n)]) mirror.failures.push(`${named}: ${n} unpaid, its mate paid`);
    const x = live[random(live.length)], y = mint.mirrorMate(x);
    if (mint.paidUpTo([...named, x], 260)[y]) mirror.failures.push(`${named} + ${x}: the mate ${y} is paid`);
    named.push(x, y); mirror.moves += 2;
  }
  mirror.games++;
}
console.log(JSON.stringify({
  table: mint.TABLE, frontier: mint.FRONTIER, lessons: mint.LESSONS.map((l) => l[0]), solved,
  minimal: mint.minimal([16, 24, 10, 32, 48]), long: mint.LONG, mirror: { ...mirror, failures: mirror.failures.slice(0, 10) },
  mates: Array.from({ length: 420 }, (_, i) => mint.mirrorMate(i + 1)),
}));
'''


def members(gens, limit):
    paid = [False] * (limit + 1)
    paid[0] = True
    for n in range(1, limit + 1):
        paid[n] = any(g <= n and paid[n - g] for g in gens)
    return paid


def gaps(gens, limit=2000):
    paid = members(gens, limit)
    return [n for n in range(1, limit + 1) if not paid[n]]


def minimal(gens):
    out = []
    for g in sorted(set(gens)):
        if not out or not members(out, g)[g]:
            out.append(g)
    return out


def is_short(half):
    """A gcd-2 position is short when its half is a quiet ender (symmetric)."""
    g = gaps(half)
    return bool(g) and 2 * len(g) == max(g) + 1


class MintTests(unittest.TestCase):
    """docs/mint.js must agree with the opening-16 ledger and the reply-38 audit."""

    @classmethod
    def setUpClass(cls):
        node = shutil.which('node')
        if node is None:
            raise unittest.SkipTest('node is not installed')
        out = subprocess.run([node, '-e', SCRIPT, str(ROOT)], capture_output=True, text=True, timeout=300, check=True)
        cls.report = json.loads(out.stdout)

    def test_answer_table_matches_the_ledger(self):
        ledger = json.loads(LEDGER.read_text())['answers']
        expected = {int(r): row['answer'] for r, row in ledger.items() if int(r) <= 36}
        table = {row[0]: row[1] for row in self.report['table']}
        self.assertEqual(table, expected)
        for reply, answer, shown, _, finite in self.report['table']:
            dest = minimal([16, reply, answer])
            self.assertEqual(shown, '{' + ', '.join(map(str, dest)) + '}', reply)
            if finite is not None:
                self.assertEqual(finite, dest, reply)
                self.assertEqual(gcd(*finite), 1, reply)

    def test_small_finite_destinations_lose_for_the_player_to_move(self):
        solved = self.report['solved']
        self.assertTrue(solved)
        for reply, result in solved.items():
            if 'error' in result:  # too large for this quick check; the ledger replays it
                self.assertIn('state limit', result['error'])
                continue
            self.assertEqual(result['move'], 0, reply)
        self.assertGreaterEqual(sum('error' not in r for r in solved.values()), 4)

    def test_frontier_lists_every_obligation_of_16_38(self):
        half_gaps = gaps([8, 19])
        obligations = sorted([2 * g for g in half_gaps] + [g for g in half_gaps if g > 1 and g % 2])
        frontier = self.report['frontier']
        self.assertEqual([r['m'] for r in frontier], obligations)
        self.assertEqual(len(frontier), 98)
        for row in frontier:
            m = row['m']
            kind = 'odd' if m % 2 else ('short' if is_short(minimal([8, 19, m // 2])) else 'long')
            self.assertEqual(row['k'], kind, m)
            self.assertIn(row['s'], {'certified', 'search', 'ladder', 'open'}, m)
            self.assertTrue(row['why'], m)

    def test_frontier_certified_moves_are_the_audited_refutations(self):
        refuted = {int(m) for m in json.loads(R38.read_text())['refuted_answers_to_38']}
        certified = {r['m'] for r in self.report['frontier'] if r['s'] == 'certified'}
        self.assertEqual(certified, refuted)
        ladder = {r['m'] for r in self.report['frontier'] if r['s'] == 'ladder'}
        self.assertEqual(ladder, {72, 88, 104, 120})

    def test_blok_mirror_pairs_every_gap_of_8_12(self):
        mates = self.report['mates']
        for x in gaps([8, 12], 400):
            y = mates[x - 1]
            if x == 1:
                self.assertIsNone(y)
                continue
            self.assertIn(y, gaps([8, 12], 420), x)
            self.assertEqual(mates[y - 1], x, x)
            self.assertLess(abs(x - y), x, x)  # 2x > y: the mirror's survival lemma needs it

    def test_blok_mirror_always_has_a_legal_answer(self):
        mirror = self.report['mirror']
        self.assertEqual(mirror['failures'], [])
        self.assertEqual(mirror['games'], 300)
        self.assertGreater(mirror['moves'], 1000)

    def test_long_lesson_matches_the_periodicity_engine(self):
        from sylver.periodicity import analyze_odd_tail
        self.assertEqual(self.report['long'], [8, 10, 22])
        self.assertEqual(gaps([4, 5, 11]), [1, 2, 3, 6, 7])
        self.assertFalse(is_short([4, 5, 11]))
        tail = analyze_odd_tail((8, 10, 22), 201)
        self.assertEqual((tail.p_values, tail.period_start, tail.period_length), ((), 49, 8))
        text = (ROOT / 'docs/mint.js').read_text()
        self.assertIn('from 49 on, the outcomes repeat every 8, and every odd move loses', text)

    def test_lessons_have_unique_ids(self):
        lessons = self.report['lessons']
        self.assertEqual(len(lessons), len(set(lessons)))
        self.assertEqual(lessons[0], 'play')
        self.assertEqual(self.report['minimal'], [10, 16, 24])


if __name__ == '__main__':
    unittest.main()
