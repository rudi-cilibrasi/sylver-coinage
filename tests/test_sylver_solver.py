import unittest

from sylver.analyze_opening_16 import exceptional_odd_wins
from sylver.analyze_g4_candidate import inspect_odd_children
from sylver.g4_candidate_certificates import (
    Move90EvenReport,
    verify_g4_candidate_even_responses,
    verify_move_90_even_partition,
    verify_move_90_short_even_refutations,
)
from sylver.eight_twelve import (
    configuration_certificate,
    eight_twelve_pair,
    holdout_even_reply_resolution,
    verify_eight_twelve_pairing,
)
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
from sylver.solver import (
    FiniteSolver,
    HoldoutOddSemigroupReport,
    frobenius_number,
    holdout_odd_semigroup_report,
    solve_position,
)


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

    def test_holdout_odd_semigroups_have_closed_form_gaps(self) -> None:
        for move in range(3, 410, 2):
            with self.subTest(move=move):
                report = holdout_odd_semigroup_report(move)
                generic = FiniteSolver((12, 16, 20, move))
                self.assertEqual(report.gaps, generic.gaps())
                self.assertEqual(report.frobenius, generic.frobenius)
        endpoint = holdout_odd_semigroup_report(409)
        self.assertIsInstance(endpoint, HoldoutOddSemigroupReport)
        self.assertEqual((endpoint.frobenius, endpoint.genus), (1235, 620))
        with self.assertRaisesRegex(ValueError, "odd integer"):
            holdout_odd_semigroup_report(410)

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
                nodes=15,
                exceptional_odd_children=154,
                even_children=169,
                external_pairing_edges=6,
                published_long_edges=4,
                native_finite_edges=1,
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
                (20, 34, "T"),
                (22, 12, "P0"),
                (24, 10, "K"),
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
                (82, 145),
                (86, 105),
            ),
        )
        self.assertEqual(
            verify_move_90_short_even_refutations(),
            (
                (4, 6, "C"),
                (8, 26, "G"),
                (78, 27, "finite"),
                (102, 57, "finite"),
            ),
        )
        self.assertEqual(
            verify_move_90_even_partition(),
            Move90EvenReport(
                legal_even_replies=30,
                short_refutations=4,
                inherited_long_refutations=(
                    (2, 3),
                    (6, 4),
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
                    (70, 277),
                    (74, 273),
                ),
                new_long_refutations=(
                    (12, 825),
                    (66, 51),
                    (82, 47),
                    (86, 227),
                    (94, 55),
                    (98, 45),
                    (114, 331),
                ),
                unresolved_long_replies=(),
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

    def test_eight_twelve_pairing_certificates(self) -> None:
        report = verify_eight_twelve_pairing()
        self.assertEqual(report.exhaustive_configurations, 1_024)
        self.assertEqual(report.parametric_configurations, 180)
        self.assertEqual(report.total_whole_pairs_checked, 10_381)

        base = configuration_certificate(False, False, (), ())
        self.assertEqual(base.generators, (8, 12))
        self.assertEqual(base.class_minima, (0, None, None, None, 12, None, None, None))
        self.assertEqual(base.whole_pairs[:4], ((2, 3), (4, 6), (5, 7), (9, 11)))

        # The mate map is an involution on every legal move except 1.
        self.assertIsNone(eight_twelve_pair(1))
        for move in (2, 3, 4, 6, 5, 7, 9, 11, 10, 14, 18, 22, 401, 403):
            mate = eight_twelve_pair(move)
            assert mate is not None
            self.assertEqual(eight_twelve_pair(mate), move)
        with self.assertRaisesRegex(ValueError, "not legal"):
            eight_twelve_pair(12)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            eight_twelve_pair(0)

        # Independent finite cross-checks: gcd-one pair completions of
        # {8,12} are P for the exact solver, and either half-pair is N with
        # the mate as a winning reply.
        for generators in ((8, 12, 5, 7), (8, 12, 13, 15), (8, 12, 13, 15, 17, 19)):
            self.assertIsNone(solve_position(generators).winning_move)
        for half, mate in ((5, 7), (9, 11), (3, 2)):
            self.assertIsNone(solve_position((8, 12, half, mate)).winning_move)

    def test_holdout_even_reply_resolution(self) -> None:
        resolution = holdout_even_reply_resolution()
        self.assertEqual(resolution.holdout, (12, 16, 20))
        self.assertEqual(resolution.winning_reply, 8)
        self.assertEqual(resolution.reached_position, (8, 12))
        self.assertEqual(resolution.candidate_branch, (12, 16, 20))
        self.assertEqual(minimal_generators((12, 16, 20, 8)), (8, 12))
        self.assertEqual(minimal_generators((16, 20, 28, 12)), (12, 16, 20))

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
