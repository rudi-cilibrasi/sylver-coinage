# Sylver move-26 hybrid campaign: even flank + parallel periodicity engine

Date: 2026-08-19
Status: approved design, awaiting implementation plan

## Context

The opening-16 certified response table answers every even move 2 through 24;
odd moves lose by Hutchings' theorem.  The frontier is move 26.  Two campaign
waves reduced it to one boundary question:

- `{16,26}` is short; its odd side is closed; children 36 and 56 refute each
  other through the certified node `V={16,26,36,56}`.
- The decisive odd-complete child 88 gave `U={16,26,88}` with 36 of 38 even
  children refuted.  The last two collapse (`98=16+82`), leaving the certified
  biconditional **`U` is N ⟺ `X={16,26,82,88}` is P**
  (`RUN_MOVE_26_U_SUBTREE.txt`).
- If `X` is N, then `U` is P and **88 answers move 26 outright**.
- `X` is long.  Exact scans refute every odd reply 3..407.  The g=2
  ultimate-periodicity engine has ground row `X+409`'s dependency closure for
  ~480 wall-clock hours: 220,574 shapes, 216,251 cached exact outcomes,
  448,043,124,906 cumulative finite-solver states — with no `P-HIT`, no
  period, and the row never completing.

Every campaign to date ran single-threaded on a 12-core, 62 GB machine, with
ascending move ordering in the exact solver even though this frontier's own
records show deep winners are the norm (291, 201, 371).  `X`'s **even**
children have never been examined; there are exactly 32 of them
(`2g` for each gap `g` of the half `<8,13,41,44>`, Frobenius 59):

```text
2 4 6 8 10 12 14 18 20 22 24 28 30 34 36 38 40 44 46 50
54 56 60 62 66 70 72 76 86 92 102 118
```

Any single even P child makes `X` N and ends the move-26 question.  If all 32
are N, those rows are a mandatory ingredient of any future `X`-is-P
certificate.  Either outcome is progress; this is the only bounded line with
a chance of immediate victory.

## Goal

Answer move 26 after opening 16: either certify a winning reply to 26 (the
expected route is `X` N ⟹ `U` P ⟹ reply 88), or certify `X` P, refuting
child 88 and pivoting the `{16,26}`-P campaign to its remaining 12 children.

## Non-goals

- No cloud compute; this machine only (12 cores, 62 GB).
- No weakening of the audit conventions: every new artifact keeps the
  fingerprint, differential-test, and exact-outcome discipline.  No outcome
  is ever inferred from search time, a finite prefix, or a heuristic.
- No community outreach in this phase (deferred, revisited at the Phase C
  timebox reviews).
- The cross-position transposition table is deferred (see §1).

## §1 Shared foundation: parallel exact-solve service

**Orchestrator.**  A new `sylver/parallel_solve.py` (~150 lines) drives
`N=10` worker processes (12 cores, 2 reserved for the system).  Each worker
invokes the existing native solver on one whole position at a time —
process-level parallelism, zero threading inside the solver core.  Results
append to the audited exact-cache row format (the same format
`move26_data/periodicity_x.cache` uses, so Phase C can consume Phase A rows
directly), written via temp-file plus atomic rename after each batch.
Duplicate keys are rejected on merge; conflicting outcomes abort the run.
A crashed or interrupted worker leaves no partial row; its position re-queues.

**Move-ordering hints (proof-safe).**  `native_solver.cpp` gains an optional
`--hints m1,m2,...` argument: candidate moves tried before the ascending
scan in `winning_move`, at the root position only (interior recursion is
memo-dominated; root-level deep winners are where the ascending scan bleeds).
Hint sources, in priority order:

1. recorded winners of sibling positions in the 216K cache (same base
   generators, one anchor differing by a small even amount);
2. a descending probe from the Frobenius number (end moves and near-end
   moves, where this frontier's winners cluster).

Ordering cannot change an outcome, only the cost of finding it.  Enforced by
a new **hint-invariance test**: a control set solved with and without hints
must produce identical outcomes and identical winning-move values where the
solver reports the least winner — note that with hints the reported winner
may differ (any winning move is a valid N-certificate); the test therefore
checks outcome equality plus independent verification that each reported
winner's child is P.  Run records state which hint list was used.

**Transposition table: deferred.**  Benchmark hints + parallelism first.
Add a TT only if profiling then shows the majority of work is redundant
sub-DAG re-derivation across sibling positions.  If added: in-memory,
per-worker, keyed by the canonical gap-set (state bitset truncated to its
own Frobenius number), never persisted across audited runs.

## §2 Phase A: even-flank sortie on X (bounded, days)

A new `sylver/analyze_x_even_flank.py` processes the 32 even children
`{16,26,82,88,2g}` in three steps:

1. **Symbolic router** (pure arithmetic, minutes).  For each child, attempt
   in order: (a) semigroup collapse identities onto already-classified
   positions (the `98=16+82` mechanism, applied systematically over all
   generator sums); (b) a routing reply into the certified node graph
   (`C,G,K,F,H,V,...`); (c) sibling absorption — a reply after which the
   child's extra generator is generated, inheriting an existing refutation.
   Every claimed route is re-verified by semigroup computation, not pattern
   matched.
2. **Quiet-ender classification.**  For each unrouted child, compute the
   half semigroup and verify the quiet-ender hypothesis explicitly before
   any Quiet End pruning (the `{10,16,24,28}` cautionary precedent: an odd
   move inside a non-quiet half can win).  Short children get their full
   finite frontier enumerated (exceptional odd children + even children).
3. **Parallel odd scans** via §1 on the survivors, with ordering hints.
   Short children close finitely.  Long children get bounded sorties with
   an explicit per-child budget (default 60 CPU-minutes per batch, revisited
   at the phase review); frontiers are recorded, never extrapolated.

**Decision gate.**

- Some child P ⟹ `X` is N ⟹ `U` is P by the campaign biconditional ⟹
  **88 answers move 26**.  Certification does not cite the biconditional's
  prose: `U`'s P-node entry in `short_certificates.py` must exhibit explicit
  N-witnesses for all 38 children — 36 already refuted, child 82 (= `X`) by
  the new P-witness, and child 98 (`{16,26,88,98}`) by its own concretely
  verified refutation (the run record asserts this follows from `X` N; the
  certifier re-derives it with an explicit P child rather than trusting the
  assertion).  Then:
  append RESEARCH.md Attempt 20, refresh STATUS.md and QUEUE.md, preserve
  `RUN_X_EVEN_FLANK.txt` with fingerprints.  The `{16,26}` classification
  then continues (26 is answered; the table's next row is move 28), and the
  periodicity engine stands down from `X`.
- All 32 N ⟹ bank the rows in the exact cache (they are the even half of a
  future `X`-is-P certificate) and proceed to Phase C.

## §3 Phase B: periodicity-engine upgrades (concurrent with Phase A runs)

1. **Batch-and-resweep parallel fallbacks.**  `exact_outcome` gains a
   collect mode: the row sweep gathers cache misses instead of solving
   inline; the batch is solved on all cores via the §1 service; the row
   re-sweeps with a warm cache.  Determinism is preserved because cache
   entries are order-independent facts and re-sweeping is exactly what the
   resume path already does.  The recurrence loop, ring, reset flags, and
   Brent comparison remain single-threaded and untouched.
2. **Ordering hints** in the embedded solver (same mechanism as §1).
3. **Checkpoint compatibility.**  Rowstate format bumps to version 2; the
   v2 loader must read the existing v1 505 MB checkpoint (memo entries are
   outcome-only and port unchanged).  The deliberate Brent-candidate reset
   on resume is retained.
4. **State-count semantics.**  `states` fields become documented as
   implementation-relative.  The matching-state-count reproduction
   convention applies only between identical algorithm versions; the
   pre-upgrade binary is retained as the differential reference for
   outcome-level comparison.

**Gates before any Phase C run:** all seven periodicity differential
controls (including `{8,10,22}`), all 19 finite-solver regressions, the
ASan/UBSan interrupt-resume control, byte compilation, warning-clean
`-std=c++20 -O2 -Wall -Wextra -pedantic` builds, plus the two new tests:
hint-invariance and parallel-vs-serial cache equality (a control row swept
serially and batch-parallel must yield identical caches).

## §4 Phase C: resume row 409 at speed

Resume the saved 220,574-shape rowstate — never rebuild it, never restart
the exhausted direct odd scan (the repository's standing rule).  Success
criteria are unchanged and explicit:

- **`P-HIT`** ⟹ `X` is N ⟹ 88 answers move 26 (same certification path as
  Phase A's gate), or
- **exact repeated stable full snapshot** ⟹ the odd tail is all-N;
  combined with Phase A's banked all-N even flank, `X` is certified P ⟹
  child 88 of `{16,26}` is refuted ⟹ the campaign pivots to the remaining
  12 open children (60, 70, 82, 86, 92, 98, 114, 118, 124, 134, 150, 166),
  with the diversification approach (mutual-refutation hunting, node `W`)
  as the planned follow-up design.

Runs are timeboxed in 5-day blocks with a review after each: shapes added,
even parts added, evaluations advanced, exact outcomes added, states/second
versus the single-threaded baseline.  **Pivot criterion:** if two
consecutive blocks show decelerating shape growth but no convergence, stop
and revisit strategy — explicitly including the deferred community option
(Sicherman requests independent confirmations; `V` and the `X` frontier are
publishable), before further compute is spent.

## Testing summary

| Test | Guards |
| --- | --- |
| Hint-invariance (new) | ordering cannot change outcomes |
| Parallel-vs-serial cache equality (new) | batch fallbacks change nothing but speed |
| Seven periodicity differential controls | engine recurrence correctness |
| 19 finite-solver regressions | solver core correctness |
| ASan/UBSan interrupt-resume | checkpoint safety under the new format |
| v1-checkpoint load test (new) | the 505 MB investment survives the upgrade |

## Risks

- **Row-409 nonconvergence** even at ~10–30x: bounded by Phase A running
  first and by the Phase C timebox/pivot rule.
- **TT complexity**: excluded from scope unless profiling proves need.
- **Hint quality**: worst case hints miss and cost one wasted child
  evaluation each — bounded overhead, no correctness exposure.
- **Checkpoint migration**: guarded by the v1-load test on a private copy
  before any real resume.
