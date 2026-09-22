# W campaign, 22 September 2026

Target: `W={16,26,62,98}`. A proof that W is P would prove
`Q={16,26,88,98}` N by reply 62, since 88=26+62. It would not
classify X, U, move 26, or opening 16 on its own.

The frontier at the end of this initial campaign is in `evidence/frontier.json`;
`evidence/proof-graph.json` records the supporting facts and their origins.
No timeout or finite odd prefix is interpreted as an outcome.
The [subsequent completed B certificate](../targeted-2026-09-22/RESULT.md)
also refutes W's move 66, leaving the seven moves recorded in
[the updated frontier](../targeted-2026-09-22/w-frontier.json).

## A deduction from an existing published position

The September 5 report lists move 72 as unresolved for W. Reply 82 reaches
the published P-position `{16,26,62,72,82}`, since 98=72+26. Thus W+72
is N, conditional on that named published result. This removes one of
the report's nine obligations. This campaign does not claim to independently
prove that published P-position.

Source: [Sicherman's P-position list](https://sicherman.net/sylver/ppos.html),
consulted 22 September 2026.

## Reconstructing the public evidence

Several obligations described as settled in historical prose were absent
from the available public cache. The campaign imports the fingerprinted
305,011-row cache, repository certificates, and September 5 release, then
recomputes missing finite results. The first 240-second native budget
completed 26 evaluations; 73 attempts timed out and remained unknown.

The first mixed batch completed another 42 evaluations within a 150-second
limit. It recovered all missing exceptional odd obligations and these even
responses:

| W move | Reply | Finite P destination | Standalone states |
| ---: | ---: | --- | ---: |
| 34 | 39 | {16,26,34,39,62} | 800,890 |
| 38 | 55 | {16,26,38,55,62,98} | 3,240,895 |
| 76 | 43 | {16,26,43,62,76,98} | 4,294,839 |

All three destinations were rerun with the standalone native evaluator
compiled before the batch modification. See `standalone-crosschecks.json`.
These are recovered supporting results, not claims of mathematical novelty.
After the first batch the exact reconstructed open moves were
66,70,86,92,102,108,118,134, matching the report minus move 72.

A second, 180-second batch completed 36 further evaluations, all N, without
closing another obligation. Across the individual pass and both batches,
104 exact evaluations completed. The batches evaluated 36,084,362 and
42,657,015 states respectively; both stopped at their time limits. W remains
unknown with the same eight open even moves. Its exceptional odd side is now
fully supported in the saved public graph, rather than merely asserted by
historical prose.

## Shared finite search

The native evaluator now accepts `--batch-file FILE`: each line is a
comma-separated gcd-one position. A single memo table serves all positions,
including positions belonging to different even branches. The common
Frobenius bound is the maximum of the individual bounds. Semigroup bits
above an individual position's Frobenius number are represented, so the
common domain gives exact, comparable states. The original recurrence,
standalone behavior, and existing odd-scan modes are unchanged.

On eight W-related controls, separate solves evaluated 11,233,234 states;
the batch evaluated 5,045,386, a 55.1% reduction. Outcomes and winning
replies matched. This is a measured benefit on this sample, not a claim
that every workload improves. Counts in batch output are **cumulative**.
Inputs and output are in `batch-benchmark-positions.txt` and
`batch-benchmark.json`.

The new mode was checked against the Python reference on 119 distinct small
canonical positions, with winning destinations checked as well, plus mixed
Frobenius bounds, a machine-word boundary, terminal positions, memo reuse,
and invalid inputs. Seven existing native-control tests also pass.

An ender strategy-stealing shortcut was tested and rejected: it slightly
increased evaluated-state counts on the completed benchmark cases and did
not finish three hard controls within eight seconds. Its patch and raw
benchmark remain here; the shortcut is not enabled in the solver.

## Reproduce and continue

From the repository root, create a fresh evidence directory:

```sh
python sylver/campaigns/w-2026-09-22/run.py \
  --output /tmp/sylver-w --budget 240 --seconds 3 --odd-limit 201
python sylver/campaigns/w-2026-09-22/batch.py \
  --output /tmp/sylver-w --seconds 150 --max-positions 100 --odd-limit 101
python -m unittest tests.test_sylver_native_batch -q
```

Run continuations one at a time. `run.py` uses the frozen September 5 tools;
`batch.py` compiles the current native solver and fingerprints it in each
receipt. Subsequent batches choose the smallest sufficient native word width.
The first two recorded batches used the eight-word default. Each batch is
bounded in time and address space, preserves completed stdout rows after
interruption, and leaves unfinished requests unknown. The historical cache
is read-only. Imported outcomes and published theorems remain explicit trust
dependencies; this is a research ledger, not a new independent verification
of all imported facts. Recorded proof graphs contain original checkout paths;
a fresh reconstruction avoids dependence on those paths.
