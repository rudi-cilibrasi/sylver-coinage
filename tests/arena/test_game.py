import json
import math
from pathlib import Path
import random
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

from sylver.arena.exact import build_tools
from sylver.arena.game import IllegalMove, Position, minimal_generators
from sylver.arena.league import ENDERS, bradley_terry, render, run_league, suite
from sylver.arena.players import PLAYERS, builtin_command, load_book
from sylver.arena.referee import play_game
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
    import json, sys, time, subprocess
    MODE = sys.argv[1]
    for line in sys.stdin:
        msg = json.loads(line)
        if msg["type"] == "hello":
            print(json.dumps({"type": "ready", "name": MODE}), flush=True)
        elif msg["type"] == "move":
            if MODE == "one": print(json.dumps({"move": 1}), flush=True)
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
    def game(self, first, second, start=(4, 5), clock=None, name='g'):
        return play_game(first, second, self.dir / name, start=start,
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


class LeagueTests(unittest.TestCase):
    def test_bradley_terry_orders_players(self):
        results = [('a', 'b')] * 8 + [('b', 'a')] * 2 + [('b', 'c')] * 8 + [('c', 'b')] * 2 + [('a', 'c')] * 9 + [('c', 'a')]
        r = bradley_terry(results, ['a', 'b', 'c'])
        self.assertGreater(r['a'], r['b']); self.assertGreater(r['b'], r['c'])
        self.assertAlmostEqual(sum(r.values()), 0, places=6)
        r = bradley_terry([('a', 'b')] * 5, ['a', 'b'])
        self.assertTrue(all(math.isfinite(v) for v in r.values()))

    def test_suites(self):
        self.assertEqual(suite('empty')[0]['start'], [])
        self.assertTrue(all(o['outcome'] == 'N' for o in suite('enders')))
        db = suite('database', seed=0, per_band=1)
        self.assertEqual(len(db), 8)
        self.assertEqual(db, suite('database', seed=0, per_band=1))
        self.assertEqual({o['outcome'] for o in db}, {'P', 'N'})

    def test_league_writes_incrementally(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'league'
            players = {n: {'name': n, 'command': builtin_command(n)} for n in ('smallest', 'random')}
            standings = run_league(players, suite('enders')[:2], out, workers=2,
                                   clock={'cpu_base': 2.0, 'cpu_increment': 0.1, 'setup_cpu': 10.0, 'setup_wall': 30.0})
            lines = (out / 'games.jsonl').read_text().splitlines()
            self.assertEqual(len(lines), 4)
            self.assertTrue((out / 'plan.json').exists() and (out / 'REPORT.md').exists())
            self.assertIn('Game results are not proofs', (out / 'REPORT.md').read_text())
            self.assertEqual(sum(v['games'] for v in standings['players'].values()), 8)
            with self.assertRaises(FileExistsError):
                run_league(players, suite('enders')[:1], out)

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


if __name__ == '__main__':
    unittest.main()
