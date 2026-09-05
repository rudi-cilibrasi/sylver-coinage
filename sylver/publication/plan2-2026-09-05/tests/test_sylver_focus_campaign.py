import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from sylver.focus_campaign import frontier, pending_checks, restore
from sylver.proof_graph import ProofGraph


class FocusCampaignTests(unittest.TestCase):
    def test_changed_seed_cache_is_rejected_before_reusing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "cache"
            cache.write_text("2,3 1\n")
            seed = Path(directory) / "seed.json"
            seed.write_text(json.dumps({"sources": {str(cache): {
                "sha256": hashlib.sha256(cache.read_bytes()).hexdigest()}},
                "support": {}}))
            graph, _ = restore(seed)
            self.assertEqual(graph.route((2, 3))["outcome"], "P")
            cache.write_text("2,3 0\n")
            with self.assertRaisesRegex(ValueError, "seed cache changed"):
                restore(seed)

    def test_discovered_witness_removes_all_work_for_resolved_parent(self):
        graph = ProofGraph()
        child = (16, 26, 60, 62, 98)
        jobs = pending_checks(graph, {child}, set(), 29)
        witness = (16, 26, 27, 60, 62, 98)
        self.assertIn(witness, jobs)
        graph.add_fact(witness, "P", {"kind": "test-fixture"})
        self.assertEqual(pending_checks(graph, {child}, set(), 29), [])
        self.assertEqual(graph.route(child)["evidence"]["move"], 27)

    def test_empty_odd_search_is_not_tail_coverage(self):
        graph = ProofGraph()
        child = (8, 10, 22)
        self.assertEqual(pending_checks(graph, {child}, set(), 1), [])
        self.assertEqual(graph.inspect(child)["outcome"], "unknown")

    def test_frontier_rejects_generated_even_move(self):
        with self.assertRaisesRegex(ValueError, "legal even moves"):
            frontier(ProofGraph(), (16, 26, 62, 98), (32,))

    def test_source_hint_beyond_scan_limit_is_a_job_not_a_fact(self):
        graph = ProofGraph()
        # Synthetic source hint; this tests scheduling, not its truth.
        child = (8, 10, 14)
        jobs = pending_checks(graph, {child}, set(), 9,
                              {'8,10,14': {101}})
        self.assertEqual(jobs[0], (8, 10, 14, 101))
        self.assertNotIn('8,10,14,101', graph.facts)


if __name__ == "__main__":
    unittest.main()
