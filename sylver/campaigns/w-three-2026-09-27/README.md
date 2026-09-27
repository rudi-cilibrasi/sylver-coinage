# Odd-reply scan of W's five open moves

This campaign continues PR #13 from W={16,26,62,98}'s five open moves
70, 86, 92, 108, 118. For each move `m` it classifies odd replies `r`,
the finite positions `W+m+r`, in increasing Frobenius order, looking for a
P destination. The discovery pass found **129 after move 86** and **139
after move 92**; see [RESULT.md](RESULT.md) for the independent replays and
the new frontier.

## Discovery

`scan/scan_w.py` runs up to five independent native evaluations at once,
each with a fresh memo, an address-space cap, and a wall limit. The
evaluator is the unchanged repository recurrence (`sylver/native_solver.cpp`)
built with `-O3 -march=native`, with 4-word states when the Frobenius number
is at most 255 and 8-word states otherwise; state counts do not depend on
the word count. Candidates skip every odd reply already classified by the
PR #13 evidence graph or the 305,011-row cache (`scan/prior-classified.json`)
and alternate between branches. A killed or over-budget query is recorded
as a failure, never as an outcome, and a P result stops that branch.

After PR #18 the scan switched to `sylver/fast_solver.cpp` (the same
recurrence with a flat memo, byte-identical output, about 1.8 times faster)
built at the narrowest word count that fits each position's Frobenius
number. Its peak memory is the final rehash, so 8-word keys exhausted a
10–11 GiB cap near Frobenius 260; those queries were recorded as failures
(`std::bad_alloc`) and retried with 5-word builds under a 12 GiB cap.

`scan/ledger.jsonl` records every completed query: position, Frobenius
number, outcome, the solver's first winning move for N, evaluated states,
CPU and wall seconds, and peak memory. N rows are single native runs; only
the two P rows were independently replayed. `audit.py` checks every row's
canonical position, Frobenius number, and winning-move legality, and
derives each branch's first unclassified odd reply:

```sh
python sylver/campaigns/w-three-2026-09-27/audit.py
```

## Negative results kept

Two orderings intended to speed up the scan made it slower and were
abandoned. Neither affected any recorded outcome, since the recurrence and
its exhaustiveness were unchanged.

- **Killer moves.** Trying replies that recently won at the same recursion
  depth before the ascending scan evaluated 7–25% *more* states on five
  campaign positions (two to four killers). The pairing prune that skips a
  reply `r > x` once `x` is answered by `r` is only sound for replies above
  the current move, and ascending order is what makes it bite. Reordering is
  sound only if that guard is kept exactly, which a differential test on 400
  random positions confirmed.
- **Root hints.** Passing the eight most frequent winning replies of a
  branch as `--hints` made `{16,26,62,70,98,105}` cost 31,291,104 states
  instead of 7,123,771 (4.4 times more). Even the true winning move 34 as
  the only hint saved just 26% (5,245,904). Failed hints are evaluated in
  full without the pairing prune. The scan ran about 40 minutes with hints
  before this control; those rows are exact and remain in the ledger.

W, Q, X, move 26, and opening 16 remain unresolved.
