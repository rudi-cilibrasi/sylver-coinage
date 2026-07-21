# Sylver Coinage after 16: research log

## Attempt 1 — 2026-07-20

### Goal

Build an independently checkable evaluator for finite Sylver positions, verify
it against published data, and reduce the opening `{16}` to its genuine
frontier before spending time on a large search.

### Exact finite evaluator

`solver.py` evaluates positions whose generators have gcd 1.  It:

1. computes the Apéry set and Frobenius number exactly;
2. represents the numerical semigroup as a bit set;
3. recursively evaluates every legal move other than the poisoned move 1;
4. memoizes positions and uses a commutative reply-pairing optimization; and
5. reports a winning move for an N-position or `P` for a losing position.

This is an outcome evaluator, not yet a compact proof-certificate generator.
The tests reproduce published small positions and the first four coprime
responses to 16.

### The important theoretical reduction

The naive hope was to find an odd `m` for which `{16,m}` is a finite
P-position.  Hutchings' theorem rules this out: every coprime two-generator
position with Frobenius number greater than 1 is an ender, hence an N-position.
Because 16 is even, every odd `m` is coprime to it.  Thus an odd response to 16
always loses and the unresolved responses are exactly the legal even integers.

For an even response `m`, let `d = gcd(16,m)`.  Since 16 is a power of two,
`d` is 2, 4, or 8 apart from the already-solved divisor replies.  Dividing
`{16,m}` by `d` gives a coprime pair and therefore a quiet ender.

The Quiet End Theorem supplies a further finite reduction for odd third moves.
An odd move already contained in the reduced numerical semigroup produces a
quiet ender and cannot win.  Only the finitely many odd gaps of that reduced
semigroup need exact checking.  `analyze_opening_16.py` performs this check.

### Reproduced results

The analyzer independently finds the published odd winning replies

| Position | Odd winning reply found |
| --- | ---: |
| `{16,6}` | 7 |
| `{16,10}` | 9 |
| `{16,18}` | 5 |

It finds no exceptional odd winning reply to `{16,14}`, consistent with the
published even replies 8 and 12.  The `{16,22}` exceptional-odd search exceeded
30 seconds and 215 MB on this implementation; the published winning reply is
the even move 12.

### Outcome

No solution to the bounty is claimed.  The useful result of this attempt is a
tested finite evaluator and a clean description of what remains: even response
families and P-position certificates at gcd 2, 4, and 8.  Merely extending the
gcd-one brute force will not settle `{16}`.

### Attempt 2 — finite certificate graph for `{12,16,22}`

The response `12` to `{16,22}` reaches the published P-position
`P0={12,16,22}`.  Dividing by two gives the quiet ender `{6,8,11}`, whose
Frobenius number is 21.  The Quiet End Theorem proves at once that every odd
move above 21 produces a quiet ender and is losing.  Only ten non-losing odd
moves below that threshold and eleven even moves remain.

`short_certificates.py` now checks this finite frontier without a heuristic
precision cutoff.  It also checks two subsidiary short P-position nodes,
`{4,6}` and `{12,16,20,22,26}`.  In total it verifies 17 exceptional odd
children and all 20 even children.  Every response reaches either an exactly
solved finite P-position or one of the named certificate nodes.

There is one explicit theorem boundary: after the even move 8 from `P0`, the
response 18 reaches `{8,12,18,22}`.  Blok's published proof gives this member
of the family `{8,12,8n+2,8n+6}` a simple infinite `(4n+1,4n+3)` pairing
strategy.  `pairing_family.py` now recognizes this family, derives its complete
finite set of even gaps, and checks every prescribed response for exact
legality.  The infinite part is still a theorem, not a cutoff: apart from the
special pairs `2 <-> 3` and `4 <-> 6`, its legal moves are partitioned as

```text
odd:   (4j+1, 4j+3),              j >= 1
even:  (8j+2, 8j+6),        1 <= j < n.
```

To see the finite even formula, divide the position by two.  The semigroup
`<4,6,4n+1,4n+3>` contains every even integer at least four and every odd
integer at least `4n+1`; its gaps are exactly `1,2,3` and the odd integers from
5 through `4n-1`.  Doubling gives precisely the displayed even moves.  Blok's
pairing argument shows that adding both members of any available pair removes
only complete remaining pairs; the smaller differences 2 and 4 are themselves
unavailable until their special pair has been completed.  Hence the mate of a
legal move is still legal, and eventually the opponent must play 1.  The tests
check the derived even set for the first 20 symbolic members and thousands of
individual response-legality obligations, while the proof supplies the
unbounded quantifier.

Thus the short certificate independently checks all finite arithmetic branches
and now also verifies that its cited infinite edge has the exact hypotheses of
the pairing theorem.  This removes a brittle hard-coded trust step, but does
not turn the family theorem into a solution of `{16}`.

This confirms a strategically important response already in the literature;
it does not settle the opening `{16}`.  A scalable attack still needs a
parametric rule covering every even second move in the gcd 2, 4, and 8
classes.

### Attempt 3 — certified finite portion of the opening strategy

The short certificate graph now also proves the published P-positions

```text
{8,14}       and       {12,14,16}.
```

Their divide-by-two semigroups are quiet enders with Frobenius number 17, so
the Quiet End Theorem handles every sufficiently large odd move.  The checker
solves all 16 exceptional odd children exactly.  It also exhausts each node's
nine legal even moves: direct gcd-one replies handle twelve of the eighteen
branches, three reach the already certified node `{4,6}`, and the other three
reach the checked first member `{8,10,12,14}` of Blok's infinite pairing
family.

Across all five named short nodes, `verify_published_short_certificates` now
checks 33 exceptional odd children, 38 even children, and four explicit edges
to the pairing theorem.  No precision cutoff is involved.

As a consequence, the following portion of a response strategy after opening
16 is proof-grade:

| Opponent's even move | Verified reply | P-position reached |
| ---: | ---: | --- |
| 2 | 3 | finite `{2,3}` |
| 4 | 6 | `{4,6}` |
| 6 | 7 | finite gcd-one node |
| 8 | 14 | `{8,14}` |
| 10 | 9 | finite gcd-one node |
| 12 | 14 | `{12,14,16}` |
| 14 | 8 | `{8,14}` |
| 18 | 5 | finite gcd-one node |
| 22 | 12 | `{12,16,22}` |

`verify_opening_16_even_responses` checks legality and every destination.
`RUN_OPENING_RESPONSES.txt` preserves source fingerprints and the complete
report.  This is useful finite coverage but deliberately not a solution:
moves 20, 24, 26, and infinitely many larger even replies still require
certified rules.

### Attempt 4 — the gcd-four candidate after move 20

The recent primary survey explicitly identifies `{16,20,28}` as a possible
gcd-four P-position.  If true, 28 would answer the still-open move 20 after
the opening 16.  `analyze_g4_candidate.py` checks a clean necessary condition:
because the candidate is all even, every odd child has gcd one and is exactly
decidable by the finite solver.  All 27 odd moves from 3 through 55 are
refuted, with an explicit winning response from the child in every case.
`RUN_G4_CANDIDATE.txt` records the complete computation.

There is also proof-grade finite progress on the even side.
`g4_candidate_certificates.py` verifies replies to nineteen legal even moves:
`2,4,6,8,10,14,18,22,24,26,30,34,38,42,46,50,54,58,62`.  Move 8 is
answered by 26, reaching the
short position `G={8,20,26}`.  The Quiet End Theorem handles G's unbounded
odd tail, while the checker exhausts its nine exceptional odd children and
ten even children.  Nine even edges finish in exact finite or pairing-family
P-positions.  The remaining edge reaches `{8,10,22}`, proved P by Sicherman's
peer-reviewed periodicity computation; this external theorem boundary is
reported explicitly rather than hidden in a cutoff.

Move 26 is now answered by 38.  Its destination
`J={16,20,26,28,38}` is short: the checker exhausts all 12 exceptional odd
and 13 even children, while the Quiet End Theorem handles every larger odd
move.  Unlike G, J has no new external long-position dependency; its only
non-finite edge reaches the already certified `{4,6}`.

Move 34 is answered by 22.  The destination
`L={16,20,22,28,34}` is another fully checked short P-position: 11
exceptional odd children and all 12 even children close locally, with only
the existing `{4,6}` certificate edge.

Move 38 is answered by 26, returning to the already certified node J.  Move
42 is answered by 30; its destination `N={16,20,28,30,42}` is short and is
checked through all 13 exceptional odd and 14 even children.  N likewise has
no theorem dependency beyond the established Quiet End Theorem and `{4,6}`.

Move 46 has the direct gcd-one response 35.  Move 50 is answered by 38,
reaching the short node `M={16,20,28,38,50}`.  M's 15 exceptional odd and 16
even children reduce to finite P-positions, earlier short nodes, and
`O={8,20,30}`.  O is itself short; its only external boundaries are the same
pairing family and published `{8,10,22}` computation already named above.

The next six branches also close directly at gcd one: move 54 is answered
by 35, moves 58 and 62 are each answered by 43, and move 66 is answered by
305.  Moves 70 and 74 are answered by 277 and 273.  These are exact finite
P-position evaluations.  The last three are materially larger: their
Frobenius numbers are 395, 371, and 371 and their independent searches evaluate
10,681,555, 11,442,992, and 12,989,520 game states respectively, so
`native_solver.cpp` implements the same bit-set recurrence in C++.  It is
compiled with warnings enabled, differentially tested against the Python
reference on small and medium controls, and independently reruns
all three positions as P in about one minute apiece.  The corresponding
`RUN_G4_MOVE_*.txt` files fingerprint the sources, controls, and results; no
precision cutoff is involved.

Move 78 returns to the smaller regime: the direct response 27 is an exact
finite P-position with Frobenius number 93 and 83,237 evaluated states.  The
Python and native evaluators agree on the outcome and state count.

Move 82 is answered by 145.  Its exact finite child has Frobenius number 251
and the independent native run proves it P after 6,835,860 states in 35
seconds.  The same differential and fingerprint controls apply; the smaller
first search range is preserved in `RUN_G4_MOVE_82.txt`.

Move 86 is answered by 105.  Its exact child has Frobenius number 215 and is
P after 4,122,547 states in a 19-second independent native run, recorded in
`RUN_G4_MOVE_86.txt`.

The next branch, move 90, has no direct odd P reply from 3 through 493.  Exact
common-bound batches classify all 246 children as N.  The scan crosses the
standard Frobenius ceiling of 511 under a separately compiled 1024-bit build;
the final batch uses 6.39 GB, so extending the same linear scan has sharply
diminishing value.
The even side has 30 legal replies.  Exactly four produce a short gcd-two
position, and all four are now refuted.  Reply 4 allows move 6 to the certified
`C={4,6}`; reply 8 allows move 26 to the certified `G={8,20,26}` (indeed
`90=26+8*8`); reply 78 allows move 27 to an exact 83,237-state P-position; and
reply 102 allows move 57 to an exact 823,941-state P-position.  The verifier
recomputes shortness rather than assuming this list and then rechecks every
destination.  The odd frontier is in `RUN_G4_MOVE_90_ODD.txt`, and the short
even refutations are fingerprinted in `RUN_G4_MOVE_90_SHORT.txt`.

This does not settle move 90.  The remaining 26 even replies are long; the
Quiet End Theorem does not make long positions N, and some may require very
large winning moves.  Nevertheless, 19 of them inherit an existing response
from the candidate graph: after that response, 90 is already in the certified
P semigroup and is redundant.  Four more have new direct odd responses:

| Long even reply | Refuting odd move | Exact P child: Frobenius / states |
| ---: | ---: | ---: |
| 12 | 825 | 923 / 5,054,234 |
| 66 | 51 | 129 / 515,419 |
| 82 | 47 | 133 / 500,069 |
| 86 | 227 | 325 / 13,220,935 |
| 94 | 55 | 157 / 786,501 |
| 98 | 45 | 147 / 437,973 |
| 114 | 331 | 433 / 23,849,826 |

Thus **all 30 legal even replies** are refuted.  The verifier recomputes the
full disjoint partition.  Reply 12 required a separately compiled 1024-bit
state: odd move 825 reaches a 5.05-million-state P-position with Frobenius
number 923.  `RUN_G4_MOVE_90_EVEN.txt` fingerprints the original 27-reply
partition; the three `RUN_G4_MOVE_90_REPLY_*.txt` records preserve the later
independent P reruns and initial frontier extensions.  The final
`RUN_G4_MOVE_90_ODD_421.txt` checkpoint records 60 more exact rows and
cross-width reruns of its final P destination.  `RUN_G4_MOVE_90_ODD_457.txt`
and `RUN_G4_MOVE_90_ODD_493.txt` add 36 later wide-build rows.  Odd replies
above 493 to the original move-90 child remain open, so move 90 itself is not
classified.

There is finite pairing structure inside the new frontier, but not yet an
unbounded rule.  Of the 96 rows from 303 through 493, 22 reciprocal pairs
cover 44 moves: for example, 399 answers 405 and 405 answers 399, so both
children reach the same exact P-position after the second move.  The same is
true of 463 and 489.  Across all 22 pairs the differences are exactly drawn
from `6,14,18,22,26,30,34,38,50,54,94,98,114`, each a legal even gap of the
move-90 position.  The endpoints do not yet yield a checked periodic or
parametric pairing, so this compresses finite certificates without addressing
the odd tail.

The first unresolved even branch 12 reduces the candidate to `{12,16,20}`.
The primary survey explicitly calls a good odd reply to this position
unknown.  An exact bounded pass now excludes every odd reply through 101:
each of the 50 children is N, with its refuting move preserved in
`RUN_12_16_20_ODD.txt`.  This records the computational frontier without
mistaking it for an unbounded answer.

This finite result is consistent with the candidate being P but does not
prove it.  A proof must still cover infinitely many larger odd moves and all
remaining legal even moves, beginning with 12 and 90; no extrapolation
from the checked range is used here.

### Sources

- George Sicherman, *The Care and Feeding of Enders*:
  <https://sicherman.net/sylver/enders.html>
- George Sicherman, published `{m,n}` outcomes:
  <https://sicherman.net/sylver/mnlist.html>
- George Sicherman, *Theory and Practice of Sylver Coinage* (2002), including
  the periodicity computation for `{8,10,22}`:
  <https://doi.org/10.5281/zenodo.7590153>
- Thomas Blok, *The 6-16 Tables* (2026):
  <https://sicherman.net/sylver/6-16Tables.pdf>
- R. Eaton, K. Herzinger, I. Pierce, and J. Thompson, *Numerical Semigroups
  and the Game of Sylver Coinage* (2020):
  <https://doi.org/10.1080/00029890.2020.1785254>
