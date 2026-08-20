import tempfile
import unittest
from pathlib import Path

from sylver.parallel_solve import RangeRow, cache_key, load_cache
from sylver.solver import FiniteSolver
from sylver.x_even_flank import (
    ChildStatus,
    EXPECTED_EVEN_CHILDREN,
    X_BASE,
    build_scan_jobs,
    classify_half,
    even_children,
    hint_pool,
    known_p_semigroups,
    route_children,
    run_campaign,
)

ROOT = Path(__file__).resolve().parents[1]
REAL_CACHE = ROOT / "sylver" / "move26_data" / "periodicity_x.cache"


class EnumerationTests(unittest.TestCase):
    def test_x_has_exactly_the_32_expected_even_children(self) -> None:
        self.assertEqual(even_children(), EXPECTED_EVEN_CHILDREN)
        self.assertEqual(len(EXPECTED_EVEN_CHILDREN), 32)

    def test_p0_has_the_eleven_even_moves_from_the_research_log(self) -> None:
        # RESEARCH.md Attempt 2: {12,16,22} has "eleven even moves".
        self.assertEqual(len(even_children((12, 16, 22))), 11)


class RouterTests(unittest.TestCase):
    def test_known_p_semigroups_contains_node_v_and_the_classic_pair(self) -> None:
        table = known_p_semigroups()
        self.assertEqual(table[(16, 26, 36, 56)], "node:V")
        self.assertIn((2, 3), table)

    def test_child_two_routes_to_the_classic_p_pair(self) -> None:
        statuses = route_children({})
        self.assertEqual(statuses[2].status, "refuted")
        self.assertEqual(statuses[2].reply, 3)
        self.assertEqual(statuses[2].destination, (2, 3))

    def test_children_36_and_56_route_into_node_v(self) -> None:
        # 26+56=82 and 16+36+36=88 collapse the destination onto V exactly.
        statuses = route_children({})
        for child, reply in ((36, 56), (56, 36)):
            self.assertEqual(statuses[child].status, "refuted")
            self.assertEqual(statuses[child].reply, reply)
            self.assertEqual(statuses[child].mechanism, "node:V")
            self.assertEqual(statuses[child].destination, (16, 26, 36, 56))

    def test_synthetic_cache_entry_refutes_a_child_via_pass_one(self) -> None:
        fake_cache = {cache_key((16, 26, 82, 88, 4, 7)): True}
        statuses = route_children(fake_cache)
        self.assertEqual(statuses[4].status, "refuted")
        self.assertEqual(statuses[4].reply, 7)
        self.assertEqual(statuses[4].mechanism, "cache")

    def test_real_cache_routing_report(self) -> None:
        statuses = route_children(load_cache(REAL_CACHE))
        refuted = [c for c, s in statuses.items() if s.status == "refuted"]
        self.assertIn(2, refuted)
        self.assertIn(36, refuted)
        self.assertIn(56, refuted)
        # Informational: how much the 216K-row investment recycles for free.
        print(
            f"\n[router] refuted {len(refuted)}/32 children:"
            f" {sorted(refuted)}"
        )


class HalfClassificationTests(unittest.TestCase):
    def test_x_half_is_not_a_quiet_ender(self) -> None:
        # Regression-locks the documented claim: <8,13,41,44> has a second
        # end, which is why X is long and the Quiet End Theorem gives no
        # odd-tail closure for X itself.
        self.assertFalse(FiniteSolver((8, 13, 41, 44)).is_quiet_ender())

    def test_quiet_child_of_p0_lists_exact_exceptional_odds(self) -> None:
        # {12,16,22} child 4 -> {4,22} (12=4*3, 16=4*4), half <2,11>, a
        # coprime pair, hence quiet, with odd gaps 3,5,7,9.
        classification = classify_half(4, base=(12, 16, 22))
        self.assertEqual(classification.child_generators, (4, 22))
        self.assertEqual(classification.half, (2, 11))
        self.assertTrue(classification.quiet)
        self.assertEqual(classification.exceptional_odds, (3, 5, 7, 9))

    def test_nonquiet_child_reports_no_exceptional_closure(self) -> None:
        for child in EXPECTED_EVEN_CHILDREN:
            if child == 2:
                continue
            classification = classify_half(child)
            if not classification.quiet:
                self.assertEqual(classification.exceptional_odds, ())

    def test_degenerate_child_two_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            classify_half(2)


class ScanJobBuilderTests(unittest.TestCase):
    def test_quiet_children_scan_their_exceptional_odds_only(self) -> None:
        statuses = {4: ChildStatus(4, "open"), 2: ChildStatus(2, "refuted", 3)}
        jobs = build_scan_jobs(statuses, base=(12, 16, 22))
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].base, (4, 22))
        self.assertEqual(jobs[0].moves, (3, 5, 7, 9))

    def test_nonquiet_children_get_a_bounded_sortie(self) -> None:
        nonquiet = [
            child
            for child in EXPECTED_EVEN_CHILDREN
            if child != 2 and not classify_half(child).quiet
        ]
        if not nonquiet:
            self.skipTest("every X child half is quiet")
        child = nonquiet[0]
        statuses = {child: ChildStatus(child, "open")}
        jobs = build_scan_jobs(statuses, sortie_moves=10)
        self.assertEqual(jobs[0].moves, tuple(range(3, 23, 2)))

    def test_hint_pool_is_deterministic(self) -> None:
        rows = [
            RangeRow((4, 22), 3, "N", 9, 25),
            RangeRow((4, 22), 5, "N", 9, 25),
            RangeRow((4, 22), 7, "N", 3, 25),
        ]
        self.assertEqual(hint_pool(rows), (9, 3))


class MiniCampaignTests(unittest.TestCase):
    def test_p0_mini_campaign_pipeline(self) -> None:
        # {12,16,22} is the certified P-position P0, so every one of its 11
        # even children is N.  The pipeline must refute most of them and
        # must certify none as P.  Children whose only winning replies are
        # even (no odd refutation exists) may surface as p_candidates;
        # that is the correct verdict of an odd-side-only scan.
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            report = run_campaign(
                base=(12, 16, 22),
                cache_path=base_dir / "seed.cache",  # empty seed
                output_directory=base_dir / "out",
                workers=2,
                sortie_moves=20,
                timeout_seconds=120.0,
                rounds=2,
            )
        self.assertEqual(len(report.statuses), 11)
        refuted = [
            c for c, s in report.statuses.items() if s.status == "refuted"
        ]
        self.assertIn(2, refuted)   # reply 3 -> {2,3}
        self.assertIn(4, refuted)   # reply 6 -> node C={4,6}
        self.assertGreaterEqual(len(refuted), 8)
        for child in report.p_candidates:
            self.assertNotIn(child, refuted)
        self.assertEqual(
            sorted(
                refuted
                + list(report.p_candidates)
                + list(report.open_children)
            ),
            sorted(report.statuses),
        )

    def test_run_record_contains_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            run_campaign(
                base=(12, 16, 22),
                cache_path=base_dir / "seed.cache",
                output_directory=base_dir / "out",
                workers=2,
                sortie_moves=5,
                timeout_seconds=60.0,
                rounds=1,
            )
            record = (base_dir / "out" / "RUN_RECORD.txt").read_text()
        self.assertIn("native_solver.cpp", record)
        self.assertIn("sha256", record.lower())
        self.assertIn("base=12,16,22", record)


if __name__ == "__main__":
    unittest.main()
