import json
import tempfile
import unittest
from itertools import combinations
from math import gcd
from pathlib import Path

from sylver.proof_graph import ProofGraph, key, membership, profile
from sylver.short_certificates import is_generated, minimal_generators
from sylver.solver import solve_position


class ProofGraphTests(unittest.TestCase):
    def test_membership_matches_independent_coin_reachability(self):
        for gs in ((4, 6), (8, 12), (8, 13, 41, 44), (7, 9, 12)):
            bits = membership(gs, 180)
            for n in range(181):
                self.assertEqual(bool(bits & (1 << n)), is_generated(gs, n))

    def test_routing_is_an_exact_identity_without_a_reply_cutoff(self):
        graph = ProofGraph()
        graph.seed_repository()
        fact = graph.route((12, 16, 20))
        self.assertEqual(fact["outcome"], "N")
        self.assertEqual(fact["evidence"]["move"], 8)
        self.assertEqual(fact["evidence"]["destination"], "8,12")
        # Structural test of the no-cutoff index. The artificial P leaf is
        # explicitly test-only; routing must still verify the identity.
        graph = ProofGraph()
        graph.add_fact((16, 26, 10001), "P", {"kind": "test-only"})
        fact = graph.route((16, 26))
        self.assertEqual(fact["evidence"]["move"], 10001)

    def test_small_routes_agree_with_exact_game_evaluation(self):
        graph = ProofGraph()
        for a in range(2, 9):
            for b in range(a + 1, 12):
                if gcd(a, b) != 1:
                    continue
                result = solve_position((a, b))
                if result.winning_move is not None:
                    graph.add_fact((a, b, result.winning_move), "P",
                                   {"kind": "exact-test-control"})
        for a in range(2, 9):
            for b in range(a + 1, 12):
                if gcd(a, b) != 1:
                    continue
                result = graph.route((a, b))
                if result and result["outcome"] == "N":
                    if result["evidence"]["kind"] == "quiet-ender-theorem":
                        self.assertTrue(solve_position((a, b)).is_winning)
                        continue
                    move = result["evidence"]["move"]
                    self.assertFalse(is_generated((a, b), move))
                    self.assertFalse(solve_position((a, b, move)).is_winning)

    def test_nonquiet_finite_routes_match_exact_triple_controls(self):
        graph = ProofGraph()
        controls = [gs for gs in combinations(range(3, 12), 3) if gcd(*gs) == 1]
        for gs in controls:
            result = solve_position(gs)
            if result.winning_move is not None:
                graph.add_fact((*gs, result.winning_move), "P", {"kind": "test-exact"})
        routed = 0
        for gs in controls:
            fact = graph.route(gs)
            if fact and fact["evidence"]["kind"] == "winning-edge":
                self.assertFalse(solve_position((*gs, fact["evidence"]["move"])).is_winning)
                routed += 1
        self.assertGreater(routed, 0)

    def test_short_position_requires_every_exceptional_and_even_move(self):
        graph = ProofGraph()
        self.assertEqual(graph.inspect((4, 6))["outcome"], "unknown")
        graph.add_fact((2, 3), "P", {"kind": "finite-terminal"})
        node = graph.inspect((4, 6))
        self.assertEqual(node["outcome"], "P")
        self.assertEqual(node["evidence"]["tail"], "quiet-end-theorem")

    def test_long_even_coverage_never_proves_p(self):
        graph = ProofGraph()
        base = (8, 10, 22)
        self.assertFalse(profile(base)["complete_moves"])
        for move in profile(base)["even_moves"]:
            graph.add_fact((*base, move), "N", {"kind": "test-only"})
        self.assertEqual(graph.inspect(base)["outcome"], "unknown")

    def test_conflicting_evidence_fails_loudly(self):
        graph = ProofGraph()
        graph.add_fact((2, 3), "P", {"kind": "test-only"})
        with self.assertRaisesRegex(ValueError, "conflicting"):
            graph.add_fact((2, 3, 4), "N", {"kind": "test-only"})

    def test_missed_route_checks_new_witnesses_after_index_grows(self):
        graph = ProofGraph()
        self.assertIsNone(graph.route((16, 26)))
        graph.add_fact((4, 6), "P", {"kind": "test-only"})
        self.assertIsNone(graph.route((16, 26)))
        graph.add_fact((16, 26, 10001), "P", {"kind": "test-only"})
        fact = graph.route((16, 26))
        self.assertEqual(fact['evidence']['move'], 10001)
        # A fresh query still searches old entries after the bound expands.
        self.assertEqual(graph.route((4, 10))['evidence']['destination'], '4,6')

    def test_quiet_ender_terminal_exception_is_preserved(self):
        graph = ProofGraph()
        self.assertEqual(graph.route((5, 7))["outcome"], "N")
        self.assertEqual(graph.inspect((2, 3))["outcome"], "P")

    def test_absorption_does_not_make_two_children_share_an_outcome(self):
        graph = ProofGraph()
        graph.seed_repository()
        # Same pattern as Q+82=X, but with independently established outcomes.
        self.assertEqual(minimal_generators((8, 10, 22, 4)), (4, 10))
        self.assertEqual(graph.route((4, 10))["outcome"], "N")
        self.assertEqual(graph.route((8, 10, 22))["outcome"], "P")
        self.assertEqual(graph.route((8, 10))["outcome"], "N")

    def test_unknown_root_export_contains_its_known_support(self):
        graph = ProofGraph()
        graph.seed_repository()
        graph.inspect((16, 26))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.json"
            graph.export(path)
            data = json.loads(path.read_text())
        self.assertEqual(data["nodes"]["16,26"]["outcome"], "unknown")
        self.assertIn("2,3", data["support"])

    def test_focused_export_preserves_unrelated_discoveries(self):
        graph = ProofGraph()
        graph.add_fact((4, 6), "P", {"kind": "test-certificate"})
        graph.inspect((5, 7))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.json"
            graph.export(path)
            data = json.loads(path.read_text())
        self.assertNotIn("4,6", data["nodes"])
        self.assertEqual(data["support"]["4,6"]["outcome"], "P")


if __name__ == "__main__":
    unittest.main()
