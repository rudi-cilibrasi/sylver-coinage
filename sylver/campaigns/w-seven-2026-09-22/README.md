# Bounded search of W's seven remaining branches

Target: W={16,26,62,98}, starting with unresolved moves
70,86,92,102,108,118,134 after the completed B certificate in PR #4.

**Result: move 134 is answered by 85**, leaving six W moves unresolved.
The search stopped after 22.4 minutes of native runtime. See the
[result and reproduction instructions](RESULT.md).

`search.py` searches for an odd reply making W+move+reply P. Such a
finite witness proves the corresponding W child N. An exhausted finite
interval or a timeout never classifies an infinite position.

The first pass uses a 3,600-second native-process wall-time budget, 90-second
batches, odd replies through 301, and an 8 GiB per-process address-space cap.
Each batch selects up to two candidates per branch. The starting branch
rotates, and each branch orders candidates by prior unsuccessful attempts,
Frobenius number, then canonical position. The first unfinished request is
deferred after a timeout; requests after it were not attempted. Thus a
deferral does not imply that a position received a whole 90 seconds.

The exact native solver is unchanged. Each batch has an initially empty
memo shared among its requests; memo tables are not retained across batches.
Completed, flushed rows survive interruption. Root P discoveries stop the
pass for independent replay. N rows also record the opponent's winning move
and its P destination, retaining that evidence for subsequent routing.

After ten 90-second batches (901.43 seconds), eight queries had completed,
all N. The remaining budget was reallocated to 300-second batches in `deep/`,
seeded from the first phase's complete graph. The first runner was stopped
between batches, with no native child active and no result left unrecorded;
`phase-transition.json` records the boundary. `search_initial.py` preserves
its exact source bytes. The current runner adds an explicit seed argument
and a `STOP` file for clean exits after a batch checkpoint. The second phase
has 2698.56 seconds, keeping the combined search budget at one hour apart
from process shutdown overhead. Compilation, graph bookkeeping, and any
independent witness replay are outside that native search budget.

The initial graph incorporates the completed B campaign and its two side
graphs. All inherited dependencies remain explicit. Each receipt records
source, executable, input, and transcript hashes, exit status, and elapsed
time. Build products are excluded from Git. Historical seed graphs retain
the original checkout paths, as documented by the preceding campaign.

Run a fresh pass from the repository root:

```sh
python sylver/campaigns/w-seven-2026-09-22/search.py \
  --output /tmp/sylver-w-seven --budget 3600 --slice 90 \
  --odd-limit 301 --memory-gib 8
python sylver/campaigns/w-seven-2026-09-22/audit.py /tmp/sylver-w-seven
```

The output directory must not exist. The audit validates bookkeeping,
hashes, legal responses, and structural proof deductions; it does not
independently replay the native finite evaluations. State counts are
cumulative within a batch. Summing them across batches counts repeated
work, and the last completed count excludes subsequent unfinished work.

`shared-pair-candidates.json` records six unresolved positions reachable
by two remaining W moves in either order. A P proof for one would close
both branches. Every candidate is long and has an unresolved odd tail;
these are possible future targets, not certificates or new outcome claims.
