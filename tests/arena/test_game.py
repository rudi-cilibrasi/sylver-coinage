from functools import reduce
from collections import Counter
import itertools
import json
import math
import os
from pathlib import Path
import random
import resource
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

from sylver.arena.common import read, sha
from sylver.arena.exact import build_tools
from sylver.arena.game import IllegalMove, Position, minimal_generators
from sylver.arena.league import (ENDERS, _fit, _native, analyze, bradley_terry, render, resolve, run_league, standings,
                                 suite, win_groups)
from sylver.arena.players import PLAYERS, builtin_command, load_book
from sylver.arena.referee import CLOCK, OTHER, Seat, clean, own_cgroup, play_game, session_cpu, text
from sylver.solver import FiniteSolver, solve_position


class RulesTests(unittest.TestCase):
    def test_minimal_generators(self):
        self.assertEqual(minimal_generators([8, 4, 6, 12]), (4, 6))
        self.assertEqual(minimal_generators([16, 26, 42]), (16, 26))
        self.assertEqual(minimal_generators([]), ())

    def test_members_and_legal_moves(self):
        p = Position([4, 6], max_move=20)
        self.assertEqual(p.legal_moves(), [2, 3, 5, 7, 9, 11, 13, 15, 17, 19])
        self.assertTrue(p.is_legal(1))
        self.assertFalse(p.is_legal(10))
        self.assertFalse(p.is_legal(21))
        for bad in (True, 0, -3, 2.0, '5', None):
            self.assertFalse(p.is_legal(bad))

    def test_play_is_immutable_and_canonical(self):
        p = Position([6, 9], max_move=100)
        q = p.play(4)
        self.assertEqual(p.generators, (6, 9))
        self.assertEqual(q.generators, (4, 6, 9))
        self.assertEqual(q.play(2).generators, (2, 9))
        self.assertEqual(q.history, (4,))
        with self.assertRaises(IllegalMove):
            q.play(10)
        with self.assertRaises(IllegalMove):
            q.play(1)

    def test_end_iff_two_and_three(self):
        rng = random.Random(7)
        for _ in range(300):
            m = rng.randint(3, 40)
            # range(2, m + 1) has only m - 1 members, so small caps take fewer.
            start = rng.sample(range(2, m + 1), rng.randint(1, min(4, m - 1)))
            p = Position(start, max_move=m)
            gaps = [n for n in range(2, m + 1) if not p.members >> n & 1]
            self.assertEqual(p.over(), not gaps)
        self.assertTrue(Position([2, 3], max_move=3).over())
        self.assertFalse(Position([2], max_move=3).over())
        self.assertEqual(Position([2], max_move=3).legal_moves(), [3])

    def test_frobenius_gcd_and_cap(self):
        self.assertEqual(Position([5, 7]).frobenius(), 23)
        self.assertEqual(Position([]).gcd(), 0)
        self.assertEqual(Position([16, 26]).gcd(), 2)
        self.assertIsNone(Position([16, 26]).frobenius())
        self.assertFalse(Position([5, 7]).capped())
        self.assertTrue(Position([16]).capped())
        self.assertTrue(Position([31, 37], max_move=100).capped())

    def test_finite_play_matches_reference_gaps(self):
        for gens in ([4, 5], [5, 7], [6, 7, 11], [8, 9, 12]):
            p = Position(gens)
            s = FiniteSolver(gens)
            self.assertEqual(p.legal_moves(), list(s.legal_moves(s.initial_state)))

    def test_rules_match_brute_force(self):
        # An independent oracle (after the reviewer's brute_rules.py): membership
        # by dynamic programming over the numbers named so far.
        def members(named, limit):
            inn = [True] + [False] * limit
            for n in range(1, limit + 1):
                inn[n] = any(g <= n and inn[n - g] for g in named)
            return inn
        rng = random.Random(12345)
        for _ in range(200):
            m = rng.randint(3, 40)
            start = rng.sample(range(2, m + 1), rng.randint(0, min(4, m - 1)))
            p, named = Position(start, max_move=m), list(start)
            while True:
                inn = members(named, m)
                gaps = [n for n in range(2, m + 1) if not inn[n]]
                self.assertEqual(p.members, sum(1 << n for n in range(m + 1) if inn[n]))
                self.assertEqual((p.legal_moves(), p.over(), p.over()), (gaps, not gaps, inn[2] and inn[3]))
                self.assertEqual([n for n in range(-2, m + 4) if p.is_legal(n)], [1] + gaps)
                self.assertEqual(p.generators, tuple(v for v in sorted(set(named))
                                                     if not members([w for w in named if w != v], v)[v]))
                self.assertEqual(p.gcd(), reduce(math.gcd, named, 0))
                if p.gcd() == 1 and max(named) <= 25:
                    big = members(named, max(named) ** 2)
                    self.assertEqual((p.frobenius(), p.capped()), (max(n for n, x in enumerate(big) if not x),
                                                                   max(n for n, x in enumerate(big) if not x) > m))
                if not gaps:
                    break
                move = rng.choice(gaps)
                p, named = p.play(move), named + [move]
                self.assertEqual(Position(start, p.history, max_move=m).members, p.members)

    def test_iterables_are_read_once(self):
        # Validation used to consume a one-shot iterator, leaving an empty start.
        self.assertEqual(Position(iter([4, 6])).generators, (4, 6))
        self.assertEqual(Position(v for v in (5, 7)).key(), '5,7')
        self.assertEqual(Position(iter([4, 5]), iter([2, 3])).history, (2, 3))
        with self.assertRaises(ValueError):
            Position(iter([1]))

    def test_rejects_bad_rules(self):
        for m in (2, True, 10.0, 1 << 21):
            with self.assertRaises(ValueError):
                Position([], max_move=m)
        with self.assertRaises(ValueError):
            Position([1])
        with self.assertRaises(ValueError):
            Position([1001])


def request(position, cpu=5.0, seat='first'):
    return {'type': 'move', 'schema': 1, 'game': 't', 'start': list(position.start),
            'history': list(position.history), 'generators': list(position.generators),
            'gcd': position.gcd(), 'seat': seat, 'ply': len(position.history) + 1,
            'rules': {'max_move': position.max_move},
            'clock': {'cpu_remaining': cpu, 'cpu_increment': 0.1, 'opponent_cpu_remaining': cpu}}


class PlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = str(build_tools('/tmp/sylver-arena-tools'))

    def test_random_is_seeded_and_legal(self):
        p = Position([5, 7])
        a = PLAYERS['random'](seed=3); b = PLAYERS['random'](seed=3)
        moves = [a.choose(p, request(p)) for _ in range(5)]
        self.assertEqual(moves, [b.choose(p, request(p)) for _ in range(5)])
        self.assertTrue(all(p.is_legal(m) and m != 1 for m in moves))

    def test_exact_plays_a_winning_move(self):
        for gens in ([4, 5], [5, 7], [6, 7, 11], [8, 9, 12], [7, 9, 11]):
            p = Position(gens)
            if not solve_position(gens).is_winning:
                continue
            move = PLAYERS['exact'](options={'binary': self.binary}).choose(p, request(p))
            self.assertFalse(solve_position(p.play(move).generators).is_winning, (gens, move))

    def test_exact_witness_search_from_infinite_position(self):
        p = Position([6])            # {6} is N: reply 4 reaches {4,6} (gcd 2, not finite);
        move = PLAYERS['exact'](options={'binary': self.binary}).choose(p, request(p))
        self.assertTrue(p.is_legal(move))   # only legality is required here

    def test_book_plays_theory_and_database(self):
        book = PLAYERS['book'](options={'binary': self.binary})
        book.setup({'rules': {'max_move': 1000}})
        empty = Position([])
        self.assertEqual(book.choose(empty, request(empty)), 5)
        self.assertEqual(load_book(1000)['5'], 'P')
        p = Position([16, 26, 62, 98, 102])
        self.assertEqual(book.choose(p, request(p)), 95)   # {16,26,62,95,98,102} is P
        p = Position([16, 26, 34])
        self.assertEqual(book.choose(p, request(p)), 151)  # {16,26,34,151} is P in the exact cache

    def test_host_protocol_round_trip(self):
        p = Position([4, 5])
        lines = [json.dumps({'type': 'hello', 'schema': 1, 'rules': {'max_move': 1000}, 'seat': 'first', 'clock': {}}),
                 json.dumps(request(p)), json.dumps({'type': 'end', 'winner': 'first', 'reason': 'x'})]
        out = subprocess.run(builtin_command('smallest'), input='\n'.join(lines) + '\n',
                             capture_output=True, text=True, timeout=30, check=True)
        replies = [json.loads(x) for x in out.stdout.splitlines()]
        self.assertEqual(replies[0]['type'], 'ready')
        self.assertEqual(replies[1]['move'], 2)


SCRIPT = textwrap.dedent('''
    import json, os, signal, sys, time, subprocess
    MODE = sys.argv[1]
    BURN = "import time,sys\\nt=time.process_time()\\nwhile time.process_time()-t<0.8:pass"
    if MODE == "sigign": signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    turns = 0
    for line in sys.stdin:
        msg = json.loads(line)
        if msg["type"] == "hello":
            if MODE == "forker" and os.fork() == 0:
                # Same session, own process group, forking sleepers without pause.
                os.setpgid(0, 0); os.closerange(0, 3)
                while True:
                    if os.fork() == 0:
                        time.sleep(30); os._exit(0)
                    time.sleep(0.002)
            if MODE == "surrogate": print(json.dumps({"type": "ready", "name": "\\ud800", "version": "\\udfff"}), flush=True)
            else: print(json.dumps({"type": "ready", "name": MODE}), flush=True)
        elif msg["type"] == "move":
            if MODE in ("one", "forker"): print(json.dumps({"move": 1}), flush=True)
            elif MODE == "surrogate": print(json.dumps({"move": 2, "note": "a\\ud800b", "claim": "\\ud800"}), flush=True)
            elif MODE == "illegal": print(json.dumps({"move": msg["generators"][0]}), flush=True)
            elif MODE == "garbage": print("not json", flush=True)
            elif MODE == "float": print(json.dumps({"move": 2.0}), flush=True)
            elif MODE == "crash": sys.exit(3)
            elif MODE == "orphan":
                # The child keeps our stdout open, so only the exit shows the crash.
                subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", sys.argv[0]])
                sys.exit(3)
            elif MODE == "sleep": time.sleep(60)
            elif MODE == "burn":
                t = time.process_time()
                while time.process_time() - t < 5: pass
            elif MODE == "child":
                subprocess.run([sys.executable, "-c", "import time\\nt=time.process_time()\\nwhile time.process_time()-t<1.5:pass"])
                print(json.dumps({"move": 2}), flush=True)
            elif MODE in ("sigign", "doublefork", "setsid", "sleeper"):
                # From the empty start, numbers in 501..1000 never generate each other.
                turns += 1
                if MODE == "sleeper": time.sleep(1.0)
                move = max(n for n in range(501, 1001) if n not in msg["history"]) if turns < 4 else 1
                print(json.dumps({"move": move}), flush=True)
                # CPU burned after replying, by processes /proc sums lose track of.
                if MODE == "sigign" and os.fork() == 0:
                    t = time.process_time()
                    while time.process_time() - t < 0.8: pass
                    os._exit(0)
                if MODE == "doublefork":
                    pid = os.fork()
                    if pid == 0:
                        if os.fork() == 0:
                            t = time.process_time()
                            while time.process_time() - t < 0.8: pass
                        os._exit(0)
                    os.waitpid(pid, 0)
                if MODE == "setsid":
                    subprocess.Popen([sys.executable, "-c", BURN, sys.argv[0]], start_new_session=True)
            elif MODE == "ponder":
                # 49 is a gap of <40,41>; the opponent then gets a turn, so the
                # CPU burned after this reply must be charged at our next turn.
                print(json.dumps({"move": 49}), flush=True)
                t = time.process_time()
                while time.process_time() - t < 1.5: pass
        else:
            break
''')
# Replies with the bytes of the Python expression in argv[1] (test-only eval).
RAW = textwrap.dedent('''
    import json, sys
    REPLY = eval(sys.argv[1])
    for line in sys.stdin:
        kind = json.loads(line)["type"]
        if kind == "hello": print(json.dumps({"type": "ready"}), flush=True)
        elif kind == "move": sys.stdout.buffer.write(REPLY); sys.stdout.flush()
        else: break
''')


class RefereeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.dir = Path(self.tmp.name)
        (self.dir / 'p.py').write_text(SCRIPT)
    def tearDown(self):
        self.tmp.cleanup()
    def scripted(self, mode):
        return {'name': mode, 'command': [sys.executable, str(self.dir / 'p.py'), mode]}
    def smallest(self):
        return {'name': 'smallest', 'command': builtin_command('smallest')}
    def game(self, first, second, start=(4, 5), clock=None, name='g', accounting=None):
        return play_game(first, second, self.dir / name, start=start, accounting=accounting,
                         clock=clock or {'cpu_base': 1.0, 'cpu_increment': 0.0, 'setup_cpu': 10.0, 'setup_wall': 30.0})

    def test_losses_are_attributed(self):
        for mode, reason in (('one', 'named-1'), ('illegal', 'illegal-move'), ('garbage', 'malformed-move'),
                             ('float', 'malformed-move'), ('crash', 'crashed'), ('burn', 'cpu-time')):
            r = self.game(self.scripted(mode), self.smallest(), name=mode)
            self.assertEqual((r['result']['loser'], r['result']['reason']), ('first', reason), mode)

    def test_sleeping_player_loses_on_wall_time(self):
        r = self.game(self.scripted('sleep'), self.smallest(), clock={'cpu_base': .2, 'cpu_increment': 0., 'setup_cpu': 10., 'setup_wall': 30.})
        self.assertEqual(r['result']['reason'], 'wall-time')

    def test_child_process_cpu_is_charged(self):
        r = self.game(self.scripted('child'), self.smallest())
        self.assertEqual((r['result']['loser'], r['result']['reason']), ('first', 'cpu-time'))

    def test_pondering_cpu_is_charged(self):
        r = self.game(self.scripted('ponder'), self.smallest(), start=(40, 41))
        self.assertEqual((r['result']['loser'], r['result']['reason']), ('first', 'cpu-time'))

    def test_normal_game_record(self):
        r = self.game(self.smallest(), self.smallest(), start=(4, 5))
        self.assertEqual(r['result']['reason'], 'opponent-must-name-1')
        self.assertTrue(r['final']['over'])
        self.assertEqual([m['move'] for m in r['moves']], [2, 3])   # {4,5}+2 -> {2,5}; +3 -> {2,3}
        self.assertEqual(r['result']['winner'], 'second')
        self.assertTrue((self.dir / 'g/record.json').exists())

    def test_crash_and_cleanup(self):
        for mode in ('crash', 'orphan'):
            r = self.game(self.scripted(mode), self.smallest(), name=mode)
            self.assertEqual(r['result']['reason'], 'crashed', mode)
            out = subprocess.run(['pgrep', '-f', str(self.dir / 'p.py')], capture_output=True, text=True)
            self.assertEqual(out.stdout.strip(), '', mode)

    def test_player_text_is_sanitized_and_recorded(self):
        # Lone surrogates survive json.loads but not UTF-8 encoding; the loss must still be recorded.
        r = self.game(self.scripted('surrogate'), self.smallest(), name='s')
        self.assertEqual((r['result']['loser'], r['result']['reason']), ('first', 'opponent-must-name-1'))
        saved = read(self.dir / 's/record.json')
        self.assertEqual(saved, r)
        self.assertEqual(saved['setup']['first']['ready'], {'name': '?', 'version': '?'})
        self.assertEqual((saved['moves'][0]['note'], saved['moves'][0]['claim']), ('a?b', None))

    def test_setup_ends_with_ready(self):
        # CPU seen above the setup cap must fail setup even if a later reading is
        # lower (session accounting loses exited processes) and no ready came.
        readings = itertools.chain([99.0], itertools.repeat(0.0))
        silent = {'name': 'silent', 'command': [sys.executable, '-c', 'import time; time.sleep(30)']}
        with mock.patch.object(Seat, 'cpu', lambda seat: next(readings)):
            r = self.game(silent, self.smallest(), name='nr')
        self.assertEqual((r['result']['loser'], r['result']['reason'], r['setup']['first']['ready']), ('first', 'setup-cpu', None))

    def test_descriptors_above_1024(self):
        # select() cannot watch descriptors >= 1024; long leagues can reach them.
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        if hard != resource.RLIM_INFINITY and hard < 1200:
            self.skipTest('cannot open 1200 descriptors')
        if soft != resource.RLIM_INFINITY and soft < 1200:
            resource.setrlimit(resource.RLIMIT_NOFILE, (1200, hard))
            self.addCleanup(resource.setrlimit, resource.RLIMIT_NOFILE, (soft, hard))
        fds = [os.open(os.devnull, os.O_RDONLY) for _ in range(1100)]
        try:
            r = self.game(self.smallest(), self.smallest(), name='fd')
        finally:
            for fd in fds:
                os.close(fd)
        self.assertEqual(r['result']['reason'], 'opponent-must-name-1')

    def test_text_and_clean(self):
        self.assertEqual(text('a\ud800b' * 3, 5), 'a?ba?')
        deep = []
        for _ in range(100000):
            deep = [deep]
        self.assertLessEqual(len(text(deep, 20)), 20)   # bounded, never a RecursionError
        self.assertEqual(clean({'x': ('\udfff', float('nan'), 1.5), '\ud800': 2}), {'x': ['?', None, 1.5], '?': 2})

    @unittest.skipUnless(own_cgroup(), 'needs a delegated cgroup v2 subtree')
    def test_cgroup_charges_cpu_that_escapes_the_session(self):
        # Auto-reaped children, double-fork orphans reaped by init, and new
        # sessions all vanish from /proc session sums; a cgroup keeps their CPU
        # and cgroup.kill reaches them. Under /proc sums they name 1 unpunished.
        for mode in ('sigign', 'doublefork', 'setsid'):
            r = self.game(self.scripted(mode), self.scripted('sleeper'), start=(), name=mode)
            self.assertEqual((r['result']['loser'], r['result']['reason']), ('first', 'cpu-time'), mode)
            self.assertEqual(r['accounting'], {'first': 'cgroup', 'second': 'cgroup'})
            out = subprocess.run(['pgrep', '-f', str(self.dir / 'p.py')], capture_output=True, text=True)
            self.assertEqual(out.stdout.split(), [], mode)
        self.assertEqual([p.name for p in own_cgroup().iterdir() if p.name.startswith('sylver-game-')
                          and str(os.getpid()) in p.name], [])

    def test_forking_player_is_fully_killed(self):
        for accounting in ('cgroup', 'session') if own_cgroup() else ('session',):
            for i in range(3):
                r = self.game(self.scripted('forker'), self.smallest(), name=f'fk-{accounting}{i}', accounting=accounting)
                self.assertEqual((r['result']['reason'], r['accounting']['first']), ('named-1', accounting))
                out = subprocess.run(['pgrep', '-f', str(self.dir / 'p.py')], capture_output=True, text=True)
                self.assertEqual(out.stdout.split(), [], f'{accounting} run {i}')

    def test_stale_pids_leave_the_outside_cache(self):
        outside = {2 ** 30}       # above pid_max, so never a live process
        session_cpu(os.getsid(0), outside)
        self.assertNotIn(2 ** 30, outside)

    def test_malformed_replies_lose(self):
        r = self.game(self.scripted('garbage'), self.smallest(), name='m')
        self.assertEqual(r['result']['reason'], 'malformed-move')
        (self.dir / 'raw.py').write_text(RAW)
        hostile = (("b'[2]\\n'", 'malformed-move'), ("b'true\\n'", 'malformed-move'),
                   ("b'{\"move\": true}\\n'", 'malformed-move'), ("b'{\"move\": \"2\"}\\n'", 'malformed-move'),
                   ("b'{\"move\": NaN}\\n'", 'malformed-move'),
                   ("b'{\"move\": ' + b'9' * 5000 + b'}\\n'", 'malformed-move'),   # beyond int() digit limit
                   ("b'{\"move\": ' + b'9' * 4000 + b'}\\n'", 'illegal-move'),
                   ("b'{\"move\": -1}\\n'", 'illegal-move'), ("b'[' * 100000 + b'\\n'", 'malformed-move'),
                   ("b'\\xff\\xfe\\n'", 'malformed-move'), ("b'x' * (2 << 20)", 'malformed-move'))
        for i, (reply, reason) in enumerate(hostile):
            player = {'name': 'raw', 'command': [sys.executable, str(self.dir / 'raw.py'), reply]}
            r = self.game(player, self.smallest(), name=f'raw{i}')
            self.assertEqual((r['result']['loser'], r['result']['reason']), ('first', reason), reply[:40])


def fake_league(games):
    """A plan and records for decided games (first, second, winner) from {4,5}."""
    names = sorted({n for g in games for n in g[:2]})
    plan = {'players': {n: {} for n in names}, 'rules': {'max_move': 1000}, 'clock': CLOCK, 'seed': 0,
            'workers': 1, 'command': None, 'schedule': [],
            'openings': [{'name': 'o', 'start': [4, 5], 'outcome': 'N', 'note': ''}]}
    records = []
    for i, (a, b, winner) in enumerate(games):
        plan['schedule'].append({'id': f'{i:04d}', 'first': a, 'second': b, 'opening': 'o', 'seed': i})
        seat = 'first' if winner == a else 'second'
        records.append({'game': f'{i:04d}', 'start': [4, 5], 'moves': [], 'setup': {'first': None, 'second': None},
                        'accounting': {'first': 'cgroup', 'second': 'cgroup'},
                        'result': {'winner': seat, 'loser': OTHER[seat], 'reason': 'opponent-must-name-1', 'detail': ''}})
    return plan, records


class LeagueTests(unittest.TestCase):
    def test_bradley_terry_orders_players(self):
        results = [('a', 'b')] * 8 + [('b', 'a')] * 2 + [('b', 'c')] * 8 + [('c', 'b')] * 2 + [('a', 'c')] * 9 + [('c', 'a')]
        r = bradley_terry(results, ['a', 'b', 'c'])
        self.assertGreater(r['a'], r['b']); self.assertGreater(r['b'], r['c'])
        self.assertAlmostEqual(sum(r.values()), 0, places=6)
        r = bradley_terry([('a', 'b')] * 5, ['a', 'b'])
        self.assertTrue(all(math.isfinite(v) for v in r.values()))

    def test_bradley_terry_reaches_the_mm_fixed_point(self):
        # The plan's MM iterations, run until strengths stop moving, define the
        # ratings; MM needed thousands of iterations on skewed or split data.
        def mm(results, players, prior=0.5):
            wins = {p: prior for p in players}; pairs = {}
            for w, l in results:
                wins[w] += 1; k = tuple(sorted((w, l))); pairs[k] = pairs.get(k, 0) + 1
            s = {p: 1.0 for p in players}
            for _ in range(10 ** 6):
                new = {p: wins[p] / (2 * prior / (s[p] + 1.0) + sum(pairs.get(tuple(sorted((p, q))), 0) / (s[p] + s[q])
                                                                    for q in players if q != p)) for p in players}
                done = max(abs(new[p] - s[p]) / new[p] for p in players) < 1e-15; s = new
                if done: break
            elo = {p: 400 * math.log10(s[p]) for p in players}
            return {p: elo[p] - sum(elo.values()) / len(elo) for p in players}
        skewed = [('a', 'b')] * 40 + [('b', 'a')] + [('b', 'c')] * 40 + [('c', 'b')] + [('a', 'c')] * 40 + [('c', 'a')]
        split = [('a', 'b')] * 17 + [('b', 'a')] * 13 + [('c', 'd')] * 20 + [('d', 'c')] * 10 + [(w, l) for w in 'ab' for l in 'cd'] * 30
        for results, players in ((skewed, 'abc'), (split, 'abcd'), ([], 'ab'), ([('a', 'b')] * 5, 'abc')):
            want, got = mm(results, players), bradley_terry(results, players)
            self.assertLess(max(abs(want[p] - got[p]) for p in players), 1e-6, results[:1])
            self.assertLess(_fit(results, list(players), .5, 100)[1], 30)

    def test_split_win_graph_gaps_are_prior_determined(self):
        # Ford's condition: without a prior the ratings exist only if the
        # directed win graph is strongly connected.
        split = ([('a', 'b', 'a')] * 17 + [('a', 'b', 'b')] * 13 + [('c', 'd', 'c')] * 20 + [('c', 'd', 'd')] * 10
                 + [(w, l, w) for w in 'ab' for l in 'cd'] * 30)
        self.assertEqual(win_groups([(g[2], g[1] if g[2] == g[0] else g[0]) for g in split], 'abcd'),
                         [['a', 'b'], ['c', 'd']])
        plan, records = fake_league(split)
        st = standings(plan, records)
        self.assertEqual(st['groups'], [['a', 'b'], ['c', 'd']])
        self.assertEqual([w['pair'] for w in st['within_groups']], [['a', 'b'], ['c', 'd']])
        self.assertGreater(st['group_gaps'][0]['prior_0.05'], st['group_gaps'][0]['prior_0.5'])
        report = render(plan, records, st)
        self.assertIn('set by the prior', report)
        self.assertIn('| Player | Group | Games | W | L | Score | Elo |', report)
        plan, records = fake_league(split + [('c', 'a', 'c')])     # one upset joins the groups
        st = standings(plan, records)
        self.assertEqual((st['groups'], st['group_gaps']), ([['a', 'b', 'c', 'd']], []))
        self.assertNotIn('set by the prior', render(plan, records, st))

    def test_suites(self):
        self.assertEqual(suite('empty')[0]['start'], [])
        self.assertTrue(all(o['outcome'] == 'N' for o in suite('enders')))
        db = suite('database', seed=0, per_band=1)
        self.assertEqual(len(db), 8)
        self.assertEqual(db, suite('database', seed=0, per_band=1))
        self.assertEqual({o['outcome'] for o in db}, {'P', 'N'})
        binary = build_tools('/tmp/sylver-arena-tools')
        for o in db:                   # the cache's outcomes, rechecked where the native solve is quick
            if Position(o['start']).frobenius() < 100:
                self.assertEqual(_native(binary, ','.join(map(str, o['start']))), o['outcome'], o['name'])

    def test_league_writes_incrementally(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'league'
            players = {n: {'name': n, 'command': builtin_command(n)} for n in ('smallest', 'random')}
            standings = run_league(players, suite('enders')[:2], out, workers=2,
                                   clock={'cpu_base': 2.0, 'cpu_increment': 0.1, 'setup_cpu': 10.0, 'setup_wall': 30.0})
            lines = (out / 'games.jsonl').read_text().splitlines()
            self.assertEqual(len(lines), 4)
            self.assertTrue((out / 'plan.json').exists() and (out / 'REPORT.md').exists())
            report = (out / 'REPORT.md').read_text()
            self.assertIn('Game results are not proofs', report)
            self.assertIn('not isolated', report)
            # Every record replays: seats alternate, moves are legal, and the
            # result names the player who had to name 1 (reviewer's recompute.py).
            plan, records = read(out / 'plan.json'), sorted(map(json.loads, lines), key=lambda r: r['game'])
            games, openings = {g['id']: g for g in plan['schedule']}, {o['name']: o for o in plan['openings']}
            for r in records:
                g, seat = games[r['game']], 'first'
                p = Position(openings[g['opening']]['start'], max_move=1000)
                self.assertEqual((r['start'], r['players']['first']['name']), (list(p.start), g['first']))
                for m in r['moves']:
                    self.assertEqual(m['seat'], seat)
                    p, seat = p.play(m['move']), OTHER[seat]
                self.assertEqual((r['final']['generators'], r['final']['over']), (list(p.generators), p.over()))
                if r['result']['reason'] == 'opponent-must-name-1':
                    self.assertEqual(r['result']['loser'], seat)
            self.assertEqual(render(plan, records, read(out / 'standings.json')), report)
            self.assertEqual(sum(v['games'] for v in standings['players'].values()), 8)
            with self.assertRaises(FileExistsError):
                run_league(players, suite('enders')[:1], out)

    def test_hostile_text_cannot_void_a_loss(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'p.py').write_text(SCRIPT)
            players = {'smallest': {'name': 'smallest', 'command': builtin_command('smallest')},
                       'poison': {'name': 'poison', 'command': [sys.executable, str(Path(d) / 'p.py'), 'surrogate']}}
            st = run_league(players, suite('enders')[:1], Path(d) / 'league', workers=2)
            self.assertEqual((st['decided'], st['void']), (2, []))
            self.assertEqual((st['players']['poison']['wins'], st['players']['poison']['losses']), (0, 2))

    def test_group_interrupt_logs_only_completed_games(self):
        # A terminal's Ctrl-C reaches the workers too: idle ones die, the pool
        # breaks, and games cut short must not be logged, not even as void.
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); out = d / 'league'
            (d / 'slow.py').write_text('import sys, time\nsys.stdin.readline()\n'
                                       'print(\'{"type": "ready"}\', flush=True)\ntime.sleep(60)\n')
            code = textwrap.dedent(f'''
                import sys
                from sylver.arena.league import run_league, suite
                from sylver.arena.players import builtin_command
                players = {{n: {{'name': n, 'command': builtin_command('random', seed=i)}} for i, n in enumerate(('r1', 'r2'))}}
                players['slow'] = {{'name': 'slow', 'command': [sys.executable, {str(d / 'slow.py')!r}]}}
                run_league(players, suite('enders')[:1], {str(out)!r}, workers=8)
            ''')
            league = subprocess.Popen([sys.executable, '-c', code], stderr=subprocess.DEVNULL, start_new_session=True)
            log, deadline = out / 'games.jsonl', time.monotonic() + 120
            while not (log.exists() and log.read_bytes().count(b'\n') >= 2) and time.monotonic() < deadline:
                time.sleep(.02)
            os.killpg(league.pid, signal.SIGINT)
            league.wait(120)
            logged = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(sorted(r['game'] for r in logged), ['0000-ender-4-5-r1-vs-r2', '0002-ender-4-5-r2-vs-r1'])
            left = subprocess.run(['pgrep', '-f', str(d / 'slow.py')], capture_output=True, text=True).stdout.split()
            self.assertEqual(left, [])

    def test_analysis_matches_a_python_recount(self):
        # After the reviewer's blunder_check.py: native analysis against the
        # Python reference solver on random games from the enders.
        binary, rng = build_tools('/tmp/sylver-arena-tools'), random.Random(5)
        plan, records = fake_league([('a', 'b', 'a'), ('b', 'a', 'a')] * 6)
        for r, start in zip(records, itertools.cycle(ENDERS)):
            p, seat, r['start'], r['moves'] = Position(start), 'first', list(start), []
            while not p.over():
                r['moves'].append({'seat': seat, 'move': rng.choice(p.legal_moves())})
                p, seat = p.play(r['moves'][-1]['move']), OTHER[seat]
        want = {n: Counter(analysed=0, from_n=0, blunders=0, unknown=0) for n in 'ab'}
        for r, g in zip(records, plan['schedule']):
            p = Position(r['start'])
            for m in r['moves']:
                q, c = p.play(m['move']), want[g[m['seat']]]
                c['analysed'] += 1
                if solve_position(p.generators).is_winning:
                    c['from_n'] += 1; c['blunders'] += solve_position(q.generators).is_winning
                p = q
        self.assertEqual(analyze(records, plan, binary, 41)['players'], {n: dict(c) for n, c in want.items()})

    def test_analysis_skips_void_games_and_caps_memory(self):
        binary = build_tools('/tmp/sylver-arena-tools')
        plan, records = fake_league([('a', 'b', 'b'), ('a', 'b', 'b')])
        for r in records:
            r['moves'] = [{'ply': 1, 'seat': 'first', 'move': 2}]    # {4,5} is N; 2 reaches {2,5}, also N
        records[1]['result'] = {'winner': None, 'loser': None, 'reason': 'void', 'detail': 'x'}
        a = analyze(records, plan, binary, 60)
        self.assertEqual(a['players']['a'], {'analysed': 1, 'from_n': 1, 'blunders': 1, 'unknown': 0})
        self.assertEqual((_native(binary, '4,5'), _native(binary, '4,5', memory_mb=1)), ('N', None))

    def test_plan_records_code_and_binary_digests(self):
        with tempfile.TemporaryDirectory() as d:
            players = {n: resolve(n, Path(d) / 'tools') for n in ('smallest', 'exact')}
            run_league(players, suite('enders')[:1], Path(d) / 'league', workers=2)
            plan = read(Path(d) / 'league/plan.json')
            code = plan['code']
            self.assertEqual(code['files']['sylver/arena/referee.py'], sha(Path('sylver/arena/referee.py').read_bytes()))
            self.assertIn('sylver/move26_data/periodicity_x.cache', code['files'])
            self.assertTrue(code['git'] is None or len(code['git']) == 40)
            binary = players['exact']['options']['binary']
            self.assertEqual(plan['players']['exact']['binary_sha256'], sha(Path(binary).read_bytes()))
            self.assertIsNone(plan['players']['smallest']['binary_sha256'])
            report = (Path(d) / 'league/REPORT.md').read_text()
            self.assertNotIn('gcd above one', report)
            self.assertIn('the empty position is capped', report)

    def test_bad_clock_is_rejected_before_any_game(self):
        players = {n: {'name': n, 'command': builtin_command(n)} for n in ('smallest', 'random')}
        with tempfile.TemporaryDirectory() as d:
            for clock in ({'cpu_base': 0}, {'cpu_increment': -1}, {'setup_wall': float('nan')}, {'cpu_base': True}):
                with self.assertRaises(ValueError, msg=clock):
                    run_league(players, suite('enders')[:1], Path(d) / 'league', clock=clock)
                self.assertFalse((Path(d) / 'league').exists())

    def test_interrupted_league_keeps_finished_games(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'league'
            code = textwrap.dedent(f'''
                from sylver.arena.league import run_league, suite
                from sylver.arena.players import builtin_command
                players = {{n: {{'name': n, 'command': builtin_command(n.rstrip('2'), seed=2)}}
                           for n in ('smallest', 'random', 'random2')}}
                run_league(players, suite('enders'), {str(out)!r}, workers=1)
            ''')
            league = subprocess.Popen([sys.executable, '-c', code], stderr=subprocess.DEVNULL)
            log, deadline = out / 'games.jsonl', time.monotonic() + 120
            while not (log.exists() and log.read_bytes().count(b'\n')) and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertIsNone(league.poll(), 'finished games must be logged while the league runs')
            league.send_signal(signal.SIGINT)
            league.wait(120)
            lines = log.read_text().splitlines()
            self.assertTrue(1 <= len(lines) < 6 * len(ENDERS))
            self.assertTrue(all(json.loads(line)['result']['reason'] for line in lines))
            # Games still running at the interrupt finish and are logged as well.
            self.assertEqual(len(lines), len(list((out / 'games').glob('*/record.json'))))
            self.assertNotEqual(league.returncode, 0)
            self.assertFalse((out / 'REPORT.md').exists())


class CliTests(unittest.TestCase):
    def test_play_smoke(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            subprocess.run([sys.executable, '-m', 'sylver.arena', 'play', 'smallest', 'random', '--start', '4,5',
                            '--games', '2', '--output', str(d / 'p')], check=True, capture_output=True)
            self.assertEqual(len(list((d / 'p').glob('*/record.json'))), 2)
        for command in ('play', 'league'):
            usage = subprocess.run([sys.executable, '-m', 'sylver.arena', command, '--help'],
                                   capture_output=True, text=True, check=True).stdout
            self.assertIn('trusted', usage)


if __name__ == '__main__':
    unittest.main()


INJECT = r'''import json, os, sys
def siblings():
    me, parent = os.getpid(), os.getppid()
    try:
        names = os.listdir('/proc')
    except OSError:
        return
    for name in names:
        if name.isdigit() and int(name) != me:
            try:
                stat = open(f'/proc/{name}/stat').read()
                if int(stat[stat.rindex(')') + 2:].split()[1]) == parent:
                    yield int(name)
            except OSError:
                pass
for line in sys.stdin:
    msg = json.loads(line)
    if msg['type'] == 'hello':
        print(json.dumps({'type': 'ready'}), flush=True)
    elif msg['type'] == 'move':
        injected = 0
        for pid in siblings():
            try:
                with open(f'/proc/{pid}/fd/1', 'w') as f:   # the opponent's stdout pipe
                    f.write(json.dumps({'move': 1}) + '\n'); injected += 1
            except OSError:
                pass
        member = {0}
        for n in range(1, 200):
            if any(n - g in member for g in msg['generators'] if g <= n):
                member.add(n)
        move = next(n for n in range(2, 200) if n not in member)
        print(json.dumps({'move': move, 'note': f'injected {injected}'}), flush=True)
    else:
        break
'''


class PlayerSandboxTests(unittest.TestCase):
    def test_sandboxed_player_cannot_inject_moves_into_its_opponent(self):
        from sylver.arena import sandbox
        from sylver.arena.league import resolve
        if sandbox.backend() == 'none':
            self.skipTest('no sandbox backend on this host')
        with tempfile.TemporaryDirectory() as d:
            script = Path(d) / 'inject.py'; script.write_text(INJECT)
            attacker = {'name': 'attacker', 'command': ['/usr/bin/python3', str(script)],
                        'sandbox': {'read': [str(script)]}, 'env': {'PATH': '/usr/bin:/bin'}}
            victim = resolve('smallest', Path(d) / 'tools')
            r = play_game(attacker, victim, Path(d) / 'game', start=(40, 41),
                          clock={'cpu_base': 5.0, 'cpu_increment': 0.1, 'setup_cpu': 10.0, 'setup_wall': 30.0})
            notes = [m.get('note') for m in r['moves'] if m['seat'] == 'first']
            self.assertTrue(notes and all(n == 'injected 0' for n in notes), notes)
            self.assertNotEqual(r['result']['reason'], 'named-1')
            self.assertEqual(r['setup']['first'].get('sandbox'), sandbox.backend())

    def test_resolve_sandboxes_by_default_with_a_minimal_environment(self):
        from sylver.arena.league import resolve
        with tempfile.TemporaryDirectory() as d:
            ext = resolve('ext', Path(d), executable='/usr/bin/true')
            self.assertEqual(ext['sandbox'], {'read': ['/usr/bin/true']})
            self.assertEqual(set(ext['env']), {'PATH', 'LANG'})
            self.assertNotIn('sandbox', resolve('ext', Path(d), executable='/usr/bin/true', sandboxed=False))
            built = resolve('smallest', Path(d))
            self.assertIn('PYTHONPATH', built['env'])
