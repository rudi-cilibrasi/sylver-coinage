import unittest

from sylver.analyze_opening_16 import exceptional_odd_wins
from sylver.analyze_g4_candidate import inspect_odd_children
from sylver.g4_candidate_certificates import verify_g4_candidate_even_responses
from sylver.pairing_family import (
    pairing_family,
    pairing_response,
    recognize_pairing_family,
)
from sylver.short_certificates import (
    CertificateReport,
    legal_moves_at_gcd_two,
    minimal_generators,
    verify_opening_16_even_responses,
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
                nodes=11,
                exceptional_odd_children=103,
                even_children=114,
                external_pairing_edges=6,
                published_long_edges=2,
            ),
        )

    def test_certified_even_responses_after_opening_sixteen(self) -> None:
        self.assertEqual(
            verify_opening_16_even_responses(),
            (
                (2, 3, "finite"),
                (4, 6, "C"),
                (6, 7, "finite"),
                (8, 14, "E"),
                (10, 9, "finite"),
                (12, 14, "F"),
                (14, 8, "E"),
                (18, 5, "finite"),
                (22, 12, "P0"),
            ),
        )

    def test_g4_candidate_bounded_odd_children(self) -> None:
        results = inspect_odd_children((16, 20, 28), 11)
        self.assertEqual(
            tuple((result.move, result.response) for result in results),
            ((3, 2), (5, 17), (7, 6), (9, 6), (11, 23)),
        )

    def test_g4_candidate_even_response_certificates(self) -> None:
        self.assertEqual(
            tuple(
                (move, response)
                for move, response, _ in verify_g4_candidate_even_responses()
            ),
            (
                (2, 3),
                (4, 6),
                (6, 4),
                (8, 26),
                (10, 9),
                (14, 31),
                (18, 5),
                (22, 29),
                (24, 5),
                (26, 38),
                (30, 29),
                (34, 22),
                (38, 26),
                (42, 30),
                (46, 35),
                (50, 38),
                (54, 35),
                (58, 43),
                (62, 43),
                (66, 305),
                (70, 277),
                (74, 273),
                (78, 27),
            ),
        )

    def test_infinite_pairing_family_even_gaps(self) -> None:
        for parameter in range(1, 21):
            with self.subTest(parameter=parameter):
                family = pairing_family(parameter)
                expected = {2, 4, 6}
                expected.update(
                    value
                    for index in range(1, parameter)
                    for value in (8 * index + 2, 8 * index + 6)
                )
                self.assertEqual(
                    set(legal_moves_at_gcd_two(family.generators)), expected
                )
                for move in expected:
                    response = pairing_response(parameter, move)
                    self.assertEqual(pairing_response(parameter, response), move)

    def test_infinite_pairing_family_odd_responses(self) -> None:
        for parameter in (1, 2, 7, 20):
            for move in range(3, 1_000, 2):
                with self.subTest(parameter=parameter, move=move):
                    response = pairing_response(parameter, move)
                    self.assertEqual(pairing_response(parameter, response), move)

    def test_pairing_family_recognition(self) -> None:
        first = recognize_pairing_family((14, 8, 10, 12))
        self.assertIsNotNone(first)
        assert first is not None
        self.assertEqual(first.parameter, 1)
        family = recognize_pairing_family((22, 12, 18, 8))
        self.assertIsNotNone(family)
        assert family is not None
        self.assertEqual(family.parameter, 2)
        self.assertIsNone(recognize_pairing_family((8, 12, 18)))


if __name__ == "__main__":
    unittest.main()
