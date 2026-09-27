import json
import random
import subprocess
import unittest

from sylver.arena.exact import build_tools
from sylver.arena.game import IllegalMove, Position, minimal_generators
from sylver.arena.players import PLAYERS, builtin_command, load_book
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

    def test_host_protocol_round_trip(self):
        p = Position([4, 5])
        lines = [json.dumps({'type': 'hello', 'schema': 1, 'rules': {'max_move': 1000}, 'seat': 'first', 'clock': {}}),
                 json.dumps(request(p)), json.dumps({'type': 'end', 'winner': 'first', 'reason': 'x'})]
        out = subprocess.run(builtin_command('smallest'), input='\n'.join(lines) + '\n',
                             capture_output=True, text=True, timeout=30, check=True)
        replies = [json.loads(x) for x in out.stdout.splitlines()]
        self.assertEqual(replies[0]['type'], 'ready')
        self.assertEqual(replies[1]['move'], 2)


if __name__ == '__main__':
    unittest.main()
