import json
import re
import shutil
import subprocess
import unittest
from math import gcd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'sylver/campaigns/o16-2026-10-09/audit.json'
R38 = ROOT / 'sylver/campaigns/r38-2026-10-09/audit.json'
SCAN = ROOT / 'sylver/campaigns/r38-2026-10-09/scan'
CAMPAIGN_P = {  # positions the campaign audits find P (their audit.json files)
    'U': ('u-2026-09-27', None), 'W': ('w-p-2026-09-27', None), 'Y': ('y-2026-10-07', None), 'Z': ('z-2026-10-08', 'Z'),
    'Z′': ('z-2026-10-08', "Z'"), 'I': ('r38-2026-10-09', 'I'), 'B24': ('r38-2026-10-09', 'B24'), 'B28': ('r38-2026-10-09', 'B28'),
    'B56': ('r38-2026-10-09', 'B56'),
}


def certified_positions():
    """Name -> generators of every certified P-position the Mint may name."""
    from sylver.short_certificates import NODES
    out = {node.name: list(node.generators) for node in NODES}
    for name, (campaign, part) in CAMPAIGN_P.items():
        audit = json.loads((ROOT / 'sylver/campaigns' / campaign / 'audit.json').read_text())
        row = audit[part] if part else audit
        assert row.get('outcome', audit.get('outcome')) == 'P' and row['complete'], name
        out[name] = row['position']
    return out


def recorded_r38_status():
    """{16,38}'s obligations that the reply-38 scan logs show N, with the evidence (as scan/status.py reads them)."""
    from sylver.arena.common import key, position, profile
    moves = profile(position((16, 38)))['moves']
    status = {}
    for line in (SCAN / 'odd_open.out').read_text().splitlines():
        m = re.match(r'move=(\d+) (\w) winning_move=(\S+)', line)
        if m and m[2] == 'N':
            status[int(m[1])] = int(m[3])
    open_odd = {71, 69, 77, 79, 85, 93, 101, 87, 109, 117, 125}   # the ledger's scan settled the other odd moves
    for m in moves:
        if m % 2 and m not in open_odd:
            status.setdefault(m, None)
    for line in (SCAN / 'odd_filter.jsonl').read_text().splitlines():
        row = json.loads(line)
        if row['P_moves']:
            status[row['r']] = row['P_moves'][0]
    known = json.loads((SCAN / 'known_p.json').read_text())
    for e in [m for m in moves if m % 2 == 0 and m not in status]:
        base = position((16, 38, e))
        hit = next((f for f in range(2, 400, 2) if key(position((*base, f))) in known and f not in base), None)
        if hit:
            status[e] = hit
    for line in (SCAN / 'resolve_16-38-long.log').read_text().splitlines():
        m = re.match(r'r=16-38 e=\s*(\d+) (\S+)\s+reply=(\S+)', line)
        if m and m[2] == 'resolved':
            status.setdefault(int(m[1]), int(m[3]))
    return moves, status

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
  named: mint.NAMED, eReplies: mint.E_REPLIES, longMax: mint.LONG_MAX,
  kunz: [...mint.KUNZ_START, [2, 3], [3, 5, 7], [4, 6, 9], [9, 10, 16], [16, 23, 36], [16, 25, 26, 44]].map((g) => ({ gens: g, ...mint.kunzColumns(g) })),
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
        for reply, answer, shown, _, finite, _ in self.report["table"]:
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
        self.assertIn('from 49 on, its analysis repeats every 8, and no odd move wins', text)
        self.assertIn('when the named numbers have greatest common divisor 2', text)

    def test_long_lesson_solves_only_quick_positions(self):
        # Each odd move x leaves a finite game that the page solves on its own thread: about
        # a second at 200 on a loaded host, but tens of seconds near 1000.
        self.assertLessEqual(self.report['longMax'], 199)
        text = (ROOT / 'docs/mint.js').read_text()
        lesson = text[text.index('function lessonLong'):text.index('// ----', text.index('function lessonLong'))]
        self.assertNotIn('999', lesson)
        self.assertIn('2 * (50 + Math.floor(Math.random() * 50)) + 1', lesson)   # the quiz asks about 101 to 199

    def test_frontier_statuses_come_from_the_committed_scans(self):
        moves, status = recorded_r38_status()
        frontier = {r['m']: r for r in self.report['frontier']}
        self.assertEqual(sorted(frontier), sorted(moves))
        ruled_out = {m for m, r in frontier.items() if r['s'] in ('search', 'certified')}
        self.assertEqual(ruled_out, set(status))
        for m, row in frontier.items():
            won = re.search(r'won by (?:the odd move )?(\d+)', row['why'])
            if won:
                self.assertEqual(int(won[1]), status[m], m)

    def test_named_positions_are_certified(self):
        certified = certified_positions()
        for name, gens in self.report['named'].items():
            self.assertIn(name, certified, name)
            self.assertEqual(gens, certified[name], name)

    def test_every_wrong_choice_in_the_quiz_is_refuted(self):
        from sylver.solver import solve_position
        named = self.report['named']
        for reply, answer, _, _, _, wrong in self.report['table']:
            self.assertEqual(len({answer, *(w[0] for w in wrong)}), 4, reply)
            paid = members([16, reply], 300)
            for x, y, name in wrong:
                self.assertFalse(paid[x], (reply, x))                       # x is a legal answer to try
                self.assertFalse(members([16, reply, x], 300)[y], (reply, x, y))   # y is a legal reply to it
                dest = minimal([16, reply, x, y])
                if name:
                    self.assertEqual(dest, named[name], (reply, x, y, name))
                else:                                                      # a finite P-position, solved here
                    self.assertEqual(gcd(*dest), 1, (reply, x, y))
                    self.assertIsNone(solve_position(dest).winning_move, (reply, x, y))

    def test_assay_replies_are_node_e(self):
        from sylver.short_certificates import NODES
        node = next(n for n in NODES if n.name == 'E')
        edges = {move: reply for move, reply, _ in node.even_responses}
        self.assertEqual({int(m): r[0] for m, r in self.report['eReplies'].items()}, edges)

    def test_kunz_columns_are_the_apery_set(self):
        for row in self.report['kunz']:
            gens, m, w, k = row['gens'], row['m'], row['w'], row['k']
            limit = max(w) + m
            paid = members(gens, limit)
            self.assertEqual(m, min(gens))
            for i in range(m):                    # w_i: the least paid amount with remainder i
                self.assertEqual(w[i], next(n for n in range(i, limit + 1, m) if paid[n]), (gens, i))
                self.assertEqual(k[i], (w[i] - i) // m)
            g = gaps(gens, limit)
            self.assertEqual(sum(k), len(g), gens)                 # the heights add up to the unpaid amounts
            self.assertEqual(row['F'], max(w) - m, gens)           # the largest unpaid amount
            self.assertEqual(row['F'], max(g), gens)
            for n in range(1, limit):                              # kunz_solver.cpp: n is a gap exactly when n / m < k_{n mod m}
                self.assertEqual(n // m < k[n % m], not paid[n], (gens, n))

    def test_kunz_lesson_memory_figure_is_the_x_record(self):
        text = (ROOT / 'docs/mint.js').read_text()
        self.assertIn('633,734,956 positions, fit in 14.2 GiB', text)
        record = (ROOT / 'sylver/campaigns/x-2026-10-06/RESULT.md').read_text()
        self.assertRegex(record, r'replay \| `kunz_solver\.cpp` \(bc5460d\) \| 1 \| P \| 633,734,956 \|.*\| 14\.2 GiB \|')

    def test_lessons_have_unique_ids(self):
        lessons = self.report['lessons']
        self.assertEqual(len(lessons), len(set(lessons)))
        self.assertEqual(lessons[0], 'play')
        self.assertEqual(self.report['minimal'], [10, 16, 24])


if __name__ == '__main__':
    unittest.main()
