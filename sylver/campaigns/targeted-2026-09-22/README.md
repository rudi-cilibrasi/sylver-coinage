# Targeted evaluation and the short move-66 branch

This continuation implements individual translated-state queries and tests
them on X and W's move-66 child. Opening 16, X, and W remain unresolved.
The main mathematical result is a complete short certificate for
**B={16,26,56,62,66} P**, using the finite reply **247** to its last
outstanding move, 76. Consequently W's move 66 is answered by 56.
The compact certificate is `b-certificate.json`; `verify_b.py` independently
replays all its finite leaves without loading the campaign cache.
The complete replay passed: all **69 finite leaves** and all **144 proof
nodes** check successfully. See the [result and response table](RESULT.md)
and `b-verification/receipt.json`.

## Exact targeted evaluation

`sylver/targeted.py` is a Python reference implementation. The native
periodicity engine accepts:

```sh
./engine CACHE ODD_TARGET --target-only EVEN_GENERATORS...
./engine CACHE ODD_LIMIT --target-only --target-start ODD_START \
  --stop-on-p EVEN_GENERATORS...
```

Each `TARGET` line classifies a finite position obtained by adjoining that
odd move. A P result supplies a winning move in the even base. N results
exclude individual moves; even an entire finite interval of N results does
not classify the infinite even base. This mode never reports a period and
neither reads nor writes automaton checkpoints. It can reuse completed exact
cache entries, including entries saved by an interrupted query.

The translated recurrence is the existing one. If the half-position has
Frobenius number f, put D=2f. At minimum odd anchor m, odd moves at most
m-D-2 eliminate all existing odd anchors and leave a singleton position.
The reset test therefore needs either one P singleton in that prefix or
exact N outcomes for the entire prefix. Targeted evaluation supplies that
history on demand, with a strictly smaller cutoff than m. It checks the
history for every queried even part, including previously registered parts.
Unknown results never advance history or become outcomes.

Before solving a missing prefix entry, the native version looks for an
already cached P singleton anywhere within the required prefix. Its anchor
is only a candidate: the canonical semigroup must match the queried even
part plus that anchor exactly. This avoids imposing an unnecessary order
on an existential proof. No semigroup-containment or outcome-monotonicity
assumption is used.

Nine targeted tests cover 80 nonmonotone Python queries, 48 cold native
queries with serial and parallel fallbacks, actual translated P hits,
cached reset witnesses, interruptions, cache reuse, ranges, and invalid
arguments. The existing periodicity suite still passes (12 passed, one
pre-existing historical-reference test skipped). An AddressSanitizer and
UndefinedBehaviorSanitizer run passed on the parallel {8,10,22} control.

## Bounded measurements

| Query | Result | Work |
| --- | --- | --- |
| X+409, initial targeted recurrence | Unknown after 90 seconds | 16 new exact N fallbacks; 481 shapes |
| X+409, cached reset lookahead | Unknown after 90 seconds | 15 new exact N fallbacks; 480 shapes |
| {16,26,62,66}+107 | N in 0.616 seconds | One new finite solve; 359,257 states |
| {16,26,62,66}, requested odd range 107–301 | Stopped at unresolved 109 | 10 new exact N fallbacks in 120 seconds |
| {16,26,62,66,109}, ordinary solver | Unknown after 60 seconds | Four-word evaluator, 6 GiB address-space limit |

The two X trials used the same original cache. They do not demonstrate a
speedup or convergence on X. The second trial's results overlap the first;
their counts must not be added as distinct discoveries. No forced kill was
needed for the targeted trials. The memory reports describe engine storage,
not peak memory of transient finite solvers.

Odd move 107 is refuted by reply 21:
`{16,21,26,62,66,107}` is P. The Python reference independently recomputed
it as P with exactly 359,257 states and Frobenius number 102. Its receipt is
`w66-107-python.json`; this check does not depend on the inherited cache.

The initial and reset-lookahead engine variants are preserved as patches
against the repository's HEAD engine at the start of this campaign
(`5868ce1`). Their reconstructed source hashes match the experiment receipts.
The current engine additionally supports targeted ranges.

## A finite alternative: reply 56

Let A={16,26,62,66}, the canonical position after W's move 66. Playing 56
gives B={16,26,56,62,66}. B is short: its half-position is a quiet ender
with Frobenius number 51. Its 14 exceptional odd obligations are now covered,
and the Quiet End Theorem handles the other odd moves. Completing the even
side, described below, establishes B P.

A complete enumeration of short even successors of W's eight outstanding
children found seven distinct positions. Six route to known N results;
B is the only one not refuted by that pass. See `w-short-frontier.json`.

The first B batch completed all 120 requested evaluations in 28.49 seconds,
using 11,133,944 shared states. It refuted move 44 by reply 21 and move 60 by
reply 33. Its remaining even obligations were then
46,50,54,70,76,86,102. A second batch completed all 160 requests in 96.81
seconds and 31,148,834 shared states. It refuted move 54 by reply 91, move
70 by reply 89, and move 102 by reply 67.

Those first two batches left 36 of 40 obligations covered, with
46,50,76,86 unresolved. The subsidiary certificates and the reply to move
86 reduced this to 39 of 40. The later reply 247 to move 76 completes all 40.
The current result is in `short56/frontier.json`, with the full evidence graph
and native transcripts beside it. The five P destinations used to close the
two batches' obligations have separate fresh-memo checks in
`short56-standalone-checks.json`. B P refutes A through reply 56 and closes
one of W's eight previously outstanding obligations.

## Two subsidiary P certificates

Let S={16,26,30,34} and T={16,26,46,50,56}. Both now have complete short
P certificates, subject to the named repository certificates and the Quiet
End Theorem. The dependency chain is:

* T+30+34=S, because 46=16+30, 50=16+34, and 56=26+30.
* B+46+50=T, because 62=16+46 and 66=16+50.

Thus S P refutes both moves 30 and 34 from T; completing T then refutes
both moves 46 and 50 from B. These are exact semigroup identities.

The two T batches completed 320 finite evaluations in 7.40 and 27.02
seconds, reducing twelve outstanding even moves to two. An S batch then
completed 160 evaluations in 2.01 seconds and 1,189,377 shared states,
closing all five outstanding S moves. The decisive replies were:

| Move from S | Winning reply |
| --- | --- |
| 28 | 71 |
| 36 | 47 |
| 44 | 43 |
| 54 | 31 |
| 70 | 57 |

`pair-certificates.json` contains the compact dependency graph for S, T,
and the two newly classified children of B. `verify_pairs.py` checks every
edge and complete cover, rejects circular support, and independently
recomputes every finite leaf using fresh Python memo tables. It loads no
campaign cache. The remaining infinite leaves are explicitly named
repository P certificates, not outcomes inferred from finite odd scans.
The independent replay passed: **94 proof nodes and all 45 finite leaves**
checked successfully. Its five named dependencies are {4,6}, {10,16,24},
{12,14,16}, {14,16,20,26}, and the pairing-family position {8,12,26,30}.
The full receipt is `pair-verification.json`. A deliberately incomplete
cover was also rejected before finite evaluation.

A third B batch completed 52 of 64 requests before its 150-second limit,
using 42,653,163 cumulative shared states. It found the alternative reply
117 to move 46 and the reply **143 to move 86**. Unfinished requests remain
unknown. A fresh native memo independently confirmed
{16,26,56,62,66,86,143} P, with Frobenius number 219 and 34,432,516 states
in 130.32 seconds; see `b86-143-standalone.json`.
The earlier targeted query of the move-86 child's odd 125 timed
out after 120 seconds, with 26 completed N fallbacks; it did not settle
that child. The direct finite search supplied the useful P witness instead.

This is evidence for recursively pursuing shared short certificates:
smaller complete covers can close several expensive long-position branches
at once. It does not show that every remaining branch has such a shortcut.
In particular, enumerating short even replies from B+76 found none that
were not already refuted by the current graph. The successful reply on
that branch was instead the odd move 247. W and opening 16 remain unresolved.

A fourth B batch completed all eight remaining requested odd replies through
169 on B+76. All eight are N, taking 171.66 seconds and 41,904,040 shared
states. Combined with the existing graph this verifies **every odd reply
3,5,...,169 is N** on B+76. This finite prefix does not classify B+76;
171 is the next unclassified odd reply. `short56-current-derived.json`
records that prefix check and fingerprints the isolated finite cache used
for the subsequent targeted query. That query, `b76-171-251`, stopped at
unresolved 171 after 120 seconds. Its eleven completed N fallback outcomes
were retained; no forced kill was needed. The requested upper limit 251
does not mean those later odd moves were evaluated.

## Completion of B: the reply 247

The next native batches excluded all odd replies through 233 on
E=B+76={16,26,56,62,66,76}. Batch 5 completed ten requested positions in
174.93 seconds and 48,346,837 shared states. Batch 6 completed nineteen
in 242.45 seconds and 58,911,534 shared states. Five machine words suffice
for these bounds; the runner now uses the exact required word count and
accepts optional root move-order hints. Hints affect search order only.
Eight controls, including positions beyond the 255 boundary, agree with
the Python reference or previously independently checked P results.

Batch 7 found **{16,26,56,62,66,76,247} P**, with Frobenius number **333**.
It completed fifteen of twenty-nine requests before its 300-second limit,
using 68,843,054 cumulative shared states. The P result was flushed and
preserved before the interruption. Unfinished later requests remain unknown.
An independent standalone solve, with an empty memo and no inherited cache,
confirmed the decisive P-position in 257.49 seconds and **60,797,798 states**;
see `b76-247-standalone.json`.
The finite witness supplies this implication chain:

```
{16,26,56,62,66,76,247} P
  => B+76 is N, by reply 247
  => B is P, by all 40 obligations and the Quiet End Theorem
  => {16,26,62,66} is N, by reply 56
  => W's move 66 is refuted (98 is redundant after 66).
```

The compact B certificate has 144 proof nodes and 69 finite leaves. It uses
the shared T certificate for both moves 46 and 50, avoiding the optional
odd-117 alternative. Six named repository P certificates remain dependencies:
{4,6}, {8,12,26,30}, {8,20,26}, {10,16,24}, {12,14,16}, and {14,16,20,26}.
No outcome from the original 305,011-row cache is needed when replaying these
finite leaves. The original cache itself has remained unchanged.

W={16,26,62,98} now has seven outstanding even moves:
**70,86,92,102,108,118,134**. This result does not classify W, X, Q, or
opening 16.

The side search also refuted every even reply from E. The three previously
unresolved replies were 36→59, 70→149, and 86→83; all three P destinations
have fresh standalone native checks in `b76-even-standalone.json`.
The first additionally has a Python replay of 3,278,048 states in
`b76-even36-python.json`. These side results are not required by B's certificate.

### Experiments that did not supply the decisive result

* Memo seeding with inherited finite P positions was tested in an isolated
  native variant. All 301 small positions and four boundary controls agreed
  with Python. On the B+86+143 control, it reduced evaluated states from
  34,432,516 to 34,425,722, only about 0.02%. The experimental patch is
  `pseed-solver.patch`; it was not adopted into the main solver. Requested
  roots were excluded from its seed. Its results retain seed dependencies.
* A full periodicity pass reached an unfinished row at odd 235, registering
  96,737 shapes on its first 150-second run. The checkpoint was resumed and
  then interrupted once the finite witness 247 made a tail proof unnecessary.
  No period or outcome is inferred from that checkpoint. Checkpoints reside
  in ignored `build/` directories; receipts fingerprint them. The full-run
  wrapper reproduced period 4 on the {6,10,14} control before use.
* A direct enumeration found 842 possible even parts and 873,081 total
  odd-offset ideals for this base (`b76-state-space.json`). This is a bound
  on the translated state space, not a period or outcome certificate.
* A fresh check of [Sicherman's table](https://sicherman.net/sylver/ppos.html)
  found S={16,26,30,34} and {16,26,36,46,56,66,76} already listed. The S
  certificate above is independent confirmation, not a novelty claim.
  Exploratory routing with the full table is recorded separately in
  `published-position-routing.json`; those extra assumptions were not
  imported into B's compact certificate.

All imported cache and published-position dependencies remain explicit in
the graphs. These records do not independently reverify the entire inherited
campaign.

## Reproduce or continue

The bounded runner builds the native source, copies the seed cache into a
temporary directory, enforces time and address-space limits, and writes only
new outcomes plus hashes and transcripts. Use a fresh label for each run:

```sh
python sylver/campaigns/targeted-2026-09-22/run.py w66-next 301 \
  16 26 62 66 --start 109 --stop-on-p --seconds 120 \
  --add-cache sylver/campaigns/targeted-2026-09-22/w-derived.cache \
  --add-cache sylver/campaigns/targeted-2026-09-22/w66-107/added.cache \
  --add-cache sylver/campaigns/targeted-2026-09-22/w66-107-301/added.cache
python -m unittest tests.test_sylver_targeted tests.test_sylver_periodicity -q
python sylver/campaigns/targeted-2026-09-22/verify_pairs.py
python sylver/campaigns/targeted-2026-09-22/verify_b.py --output /tmp/b-check
```

B's certificate is complete. Further research should use the seven remaining
W branches. Run only one writer per evidence directory. Batch counts are
cumulative; each requested position and every completed row is saved even
when a batch times out.

Historical receipts and exploratory proof graphs retain the original
checkout paths as provenance. The compact certificate verifiers resolve
their code and inputs relative to this checkout and do not read those
historical paths. Reconstruct an exploratory graph before continuing it
from a different checkout. Binaries and large periodicity checkpoints in
`build/` directories are excluded from Git; their receipts retain hashes.
