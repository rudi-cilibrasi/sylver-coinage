import random
import unittest

from sylver.arena.game import IllegalMove, Position, minimal_generators
from sylver.solver import FiniteSolver


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


if __name__ == '__main__':
    unittest.main()
