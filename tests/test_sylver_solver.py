import unittest

from sylver.analyze_opening_16 import exceptional_odd_wins
from sylver.short_certificates import (
    CertificateReport,
    legal_moves_at_gcd_two,
    minimal_generators,
    verify_published_short_certificates,
)
from sylver.solver import FiniteSolver, frobenius_number, solve_position


class FiniteSolverTests(unittest.TestCase):
    def test_frobenius_number_for_coprime_pair(self) -> None:
        self.assertEqual(frobenius_number((5, 7)), 23)

    def test_terminal_position_is_losing(self) -> None:
        solution = solve_position((2, 3))
        self.assertFalse(solution.is_winning)
        self.assertIsNone(solution.winning_move)

    def test_published_small_winning_moves(self) -> None:
        # Values from George Sicherman's published {m,n} table.  Some
        # positions have several winning moves; the solver returns the least.
        expected = {
            (4, 5): 11,
            (5, 6): 19,
            (4, 7): 13,
            (5, 7): 8,
            (6, 7): 16,
            (5, 8): 7,
            (7, 8): 5,
        }
        for position, move in expected.items():
            with self.subTest(position=position):
                self.assertEqual(solve_position(position).winning_move, move)

    def test_first_coprime_replies_to_sixteen(self) -> None:
        expected = {
            (3, 16): 2,
            (5, 16): 18,
            (7, 16): 6,
            (9, 16): 10,
        }
        for position, move in expected.items():
            with self.subTest(position=position):
                self.assertEqual(solve_position(position).winning_move, move)

    def test_coprime_pair_is_a_quiet_ender(self) -> None:
        for response in range(3, 32, 2):
            with self.subTest(response=response):
                self.assertTrue(FiniteSolver((16, response)).is_quiet_ender())

    def test_exceptional_odd_wins_reproduce_published_responses(self) -> None:
        self.assertEqual(exceptional_odd_wins(6), (7,))
        self.assertEqual(exceptional_odd_wins(10), (9,))
        self.assertEqual(exceptional_odd_wins(18), (5,))

    def test_non_coprime_position_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "gcd 1"):
            FiniteSolver((16, 18))

    def test_minimal_generators_remove_redundancy(self) -> None:
        self.assertEqual(minimal_generators((4, 6, 8, 10, 22)), (4, 6))

    def test_even_moves_of_published_short_position(self) -> None:
        self.assertEqual(
            legal_moves_at_gcd_two((12, 16, 22)),
            (2, 4, 6, 8, 10, 14, 18, 20, 26, 30, 42),
        )

    def test_published_short_certificate_graph(self) -> None:
        self.assertEqual(
            verify_published_short_certificates(),
            CertificateReport(
                nodes=3,
                exceptional_odd_children=17,
                even_children=20,
                external_pairing_edges=1,
            ),
        )


if __name__ == "__main__":
    unittest.main()
