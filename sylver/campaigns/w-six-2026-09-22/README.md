# Continuation from W's six remaining branches

This campaign continues PR #5 from its final evidence graph, searching the
six unresolved moves 70,86,92,102,108,118 of W={16,26,62,98}.
The discovery pass found **reply 95 to move 102**. See [RESULT.md](RESULT.md)
for the verification result and the remaining frontier.

## Discovery

The unchanged exact native solver completed 15 finite queries in **400.99
seconds**: 14 N and one P. The first batch completed all 12 requests in
239.19 seconds. The second completed three in 161.80 seconds before the
runner observed the flushed P result and stopped the process. Its remaining
nine requests are unclassified by that batch. A 30-minute native runtime
budget was set; unused time was not spent after the discovery.

Each batch starts with an empty shared memo. Up to two requests per branch
are interleaved, rotating the starting branch between batches. Candidates
are ordered by prior unfinished attempts, Frobenius number, and canonical
position. Batches have a five-minute wall-time limit and an 8 GiB
address-space cap. Completed N rows retain their winning P destinations,
which can route further queries without evaluation. No timeout or finite
scan prefix classifies an infinite position.

`search.py` preserves the scheduler used for discovery. `audit.py` checks
input and transcript hashes, accounting, legal replies, and derived proof
edges. Its output is [audit.json](audit.json); this structural audit is
separate from independent solver replay. State counts in batch receipts
are cumulative, with repeated work across batches.

Run a fresh reproduction from the repository root:

```sh
python sylver/campaigns/w-six-2026-09-22/search.py \
  --output /tmp/w-six-search --budget 1800 --slice 300 \
  --odd-limit 301 --memory-gib 8
python sylver/campaigns/w-six-2026-09-22/audit.py /tmp/w-six-search
```

The output directory must be new. Historical exploratory graphs retain
absolute paths to their inherited caches; these must be reconstructed to
continue from a different checkout. The compact certificates and the
reusable finite replay command resolve source files relative to the checkout
and do not require those historical paths or caches.

## Reusable finite reply verification

`python -m sylver.verify_finite_reply --certificate FILE --output NEW_DIR`
validates a schema-1 two-move path and replays its claimed finite P destination
with an empty native memo. `--python` adds an independent Python replay and
requires matching outcomes, Frobenius bounds, and exact evaluated-state counts.
The new command also accepts PR #5's existing `w134-certificate.json`.

It checks canonical generators, legal moves, the semigroup identity, and a
finite destination before starting solvers. A legal path alone does not prove
P: an N result rejects the certificate. Interrupted or rejected replays retain
incomplete receipts and transcript hashes. Existing output directories are
never overwritten. Five new tests cover structural rejection, actual native
and Python replay outside the checkout, false P claims, timeouts, and overwrite
refusal. These and the three native batch tests plus the native reference
control test all passed (nine tests).

```sh
python -m unittest tests.test_sylver_finite_reply \
  tests.test_sylver_native_batch \
  tests.test_sylver_native_solver.NativeSylverSolverTests.test_native_solver_matches_reference_controls -q
```

## Exploratory optimization

`gap-scan-experiment.patch` records an isolated candidate that iterates set
bits of the legal-move mask instead of scanning every integer. Two runs of
each variant on {16,26,37,62,87,92,98} agreed on P and 3,458,311 states.
Baseline times were 6.16 and 6.12 seconds; candidate times were 6.02 and 6.04
seconds. The separate discovery worker was also running. This one control
does not establish a general speedup, and the candidate was not adopted.
Sources, binaries, compiler flags, and timings are fingerprinted in
[gap-scan-experiment.json](gap-scan-experiment.json). Apply the patch to
`sylver/native_solver.cpp` at commit `1d94c24` in an isolated checkout to
reconstruct it. All campaign results use the unchanged repository solver.
