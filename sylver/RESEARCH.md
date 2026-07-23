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

The most immediate gap-30 extrapolation also fails exactly.  A fresh 1024-bit
evaluation finds `{16,20,28,90,495,525}` is N, with winning move 507,
Frobenius number 549, and 37,733,367 states.  This is recorded alongside the
period-493 frontier and is evidence against that finite pattern becoming a
simple translated family; it is not a classification of direct reply 495.

The first unresolved even branch 12 reduces the candidate to `{12,16,20}`.
The primary survey explicitly calls a good odd reply to this position
unknown.  The initial exact pass excluded every odd reply through 101.  A
native shared-state continuation now extends that frontier through **409**:
all 204 odd children are N, with a winning response preserved for every one.
The semigroup at every one of these children has an unbounded closed form.
For odd `m`,

```text
<12,16,20> = {0} union {4t : t >= 3},
```

and four copies of `m` already lie in that even subsemigroup.  Reduce the
coefficient of `m` to `k=0,1,2,3`.  In the residue class `km (mod 4)`, every
positive integer below `km` is a gap, `km` is represented, `km+4` and `km+8`
are gaps, and every later integer is represented.  These four classes give
all gaps exactly.  In particular,

```text
F(<12,16,20,m>) = 3m+8,
genus(<12,16,20,m>) = (3m+13)/2.
```

`holdout_odd_semigroup_report` constructs the complete formula and compares
it with the independent generic Apéry/bitset engine for every odd `m` through
409.  This explains the linear Frobenius column and gives a parametric legal-
move domain, but it does not determine the P/N outcome of its children.  It
also pinpoints why the standard symmetry criterion does not apply.  Here `F`
is odd and

```text
genus = (F+5)/2 = (F+1)/2 + 2,
```

so the semigroup is never symmetric; it cannot be pseudo-symmetric because
its Frobenius number is odd.  The known theorem that either kind of semigroup
gives an N-position therefore leaves this defect-two family untouched.
Moreover, the gap formula shows that the only pseudo-Frobenius numbers are
`3m+4` and `3m+8`: every lower gap remains a gap after adding at least one
generator, while both displayed top gaps become represented after adding any
positive semigroup element.  Since each exceeds half the Frobenius number,
they are exactly the two legal end moves.  Thus the one-ender strategy-
stealing theorem also fails uniformly for this type-two family.  See
`RUN_12_16_20_SEMIGROUP_FORMULA.txt`.

The same formula reduces a more careful strategy-stealing attempt to two
parametric exceptions.  Put `F=3m+8` and provisionally play `F`.  Every other
gap `x` except

```text
2m+4, 3m+4
```

makes `F` representable.  For a below-anchor gap in residue class `jm`, write
`jm-x=d`, where `d` is a positive multiple of four; then
`F-x=(3-j)m+(8+d)` is already in the old semigroup.  The top gaps `jm+8`
give `F-x=(3-j)m`.  Among the gaps `jm+4`, two copies of 4 leave `3m`, two
copies of `m+4` leave `m`, while `2m+4` and `3m+4` are the only failures.

If the position after the provisional `F` is P, `F` wins directly.  If it is
N and has a winning reply outside those two exceptions, that reply already
eliminates `F`, so playing it directly reaches the same P-position.  Hence
the only way this strategy-stealing probe can fail is if all its winning
replies are confined to `2m+4` and `3m+4`.  The finite frontier always finds
a nonexceptional reply, but proving that for every odd `m` is exactly the
unbounded step still missing.

The latest 2048-bit batch reaches `F=1235`, evaluates 53,604,605 cumulative
states, and peaks at 15.70 GB.  Its final response 1007 reaches the
independently rerun P-position `{12,16,20,409,1007}`, with Frobenius number
1015 and 33,717,278 evaluated states under clean 1024- and 2048-bit tables.
Across the full frontier, 42 reciprocal response pairs compress 84 rows; they
remain finite pairings, not a tail theorem.  `RUN_12_16_20_ODD.txt` preserves
the initial pass;
`RUN_12_16_20_ODD_281.txt`, `RUN_12_16_20_ODD_337.txt`, and
`RUN_12_16_20_ODD_361.txt`, `RUN_12_16_20_ODD_385.txt`, and
`RUN_12_16_20_ODD_409.txt` record the native continuations and endpoint
checks.  The latest batch's double-digit-gigabyte table triggers the explicit
stopping rule: resume only for an infinite pairing, periodicity, or another
parametric tail theorem.  This remains a finite frontier, not an unbounded
answer.

This finite result is consistent with the candidate being P but does not
prove it.  A proof must still cover infinitely many larger odd moves and all
remaining legal even moves, beginning with 12 and 90; no extrapolation
from the checked range is used here.

### Attempt 5 — the holdout `{12,16,20}` falls to an even reply

The entire odd frontier above was aimed at the wrong side of the position.
Blok's report *Sylver Coinage positions with g=2* (2021) proves that
`{8,12}` is a P-position by the simple pairing strategy, yet its conclusion
states "the completion requires knowing a good, odd reply to `{12,16,20}`,
which so far, I do not know," and this repository inherited that framing.
The overlooked fact is one identity:

```text
<12,16,20,8> = <8,12>        (16 = 8+8,  20 = 8+12),
```

and `8` is a gap of `<12,16,20>`.  So the holdout `{12,16,20}` is an
**N-position with the even winning reply 8**, reaching Blok's P-position
exactly.  The gcd-four candidate branch after its even move 12 satisfies
`<16,20,28,12> = <12,16,20>` via `28 = 12+16`, so that branch is refuted by
the same reply.  No tail theorem over the family `F(<12,16,20,m>) = 3m+8`
is required; the 409-deep frontier and its 15.70 GB tables answered a
question whose resolution was two composition identities away.

`eight_twelve.py` makes the cited pairing theorem proof-grade in this
repository's own terms.  The pairing on the gaps of `<8,12>` is `2<->3`,
`4<->6`, `(4j+1,4j+3)`, and `(8j+2,8j+6)` with `1` unpaired.  For an
arbitrary finite set of completed pairs, the configuration monoid's
residue classes modulo eight are computed exactly (a class is nonempty
exactly when its residue lies in the submonoid of `Z/8` generated by the
generator residues, and any nonempty class attains its minimum within
seven generator additions), which describes the infinite gap classes with
no cutoff.  The gap-structure lemma (gaps are always `{1}` plus whole
pairs), the mate-survival lemma (the mate of a played member stays legal
because the pair differences `1,2,4` only enter the monoid after the pair
that contains them is gone), and a termination argument (even-pair
completions strictly decrease the least completed index; the first odd or
special completion leaves finitely many gaps) close the strategy.  The
audit covers 1,204 configurations and 10,381 whole-pair checks, and the
exact finite solver independently confirms gcd-one instances.  See
`RUN_EIGHT_TWELVE.txt`.

Consequences for the opening-16 campaign.  The certified response table's
next open move 20 no longer routes through the `{16,20,28}` candidate
alone: Sicherman's independently published P-position list also claims
`{16,20,34}`, whose divide-by-two quiet ender `{8,10,17}` has Frobenius
number 39, leaving 13 exceptional odd children and 20 even children — the
same shape this repository already certifies routinely.  Verifying it
would answer move 20 outright.  The list likewise claims `{10,16,24}`
(Blok's g=2 report analyzes all even positions containing a number up to
10), which would answer move 24 by the reply 10.  Both verifications are
now the highest-value finite computations in this campaign, ahead of any
further odd-frontier extension.

### Attempt 6 — moves 20 and 24 after opening 16 are answered

Sicherman's P-position list carries the explicit request "I welcome
independent confirmation (or refutation)."  This attempt supplies
proof-grade confirmations that close the two lowest open rows of the
certified opening-16 response table.

**Move 24 is answered by 10.**  The new short node `K={10,16,24}`
(claimed P in Blok's g=2 report) is certified: its half `<5,8,12>` is a
verified quiet ender with Frobenius 19, the nine bounded odd children are
refuted exactly, and the ten even children close through `{2,3}`, `{4,6}`,
two published `{8,10,22}` periodicity edges (note `<10,16,24,8>=<8,10>`),
and exact finite P-positions, including Blok's replies 31, 5, and 47
after the even moves 12, 28, and 38.  A cautionary detail: this
repository's earlier shorthand "an odd move in the reduced semigroup
cannot win" is valid only when the half is a quiet ender, a hypothesis
`verify_published_short_certificates` has always enforced; the position
`{10,16,24,28}`, whose half has a second end at 9, is answered by the odd
move 5 *inside* its half, exactly as Blok's table says.

**Move 20 is answered by 34.**  The new short node `T={16,20,34}` is
certified P, superseding the entire `{16,20,28}` gcd-four candidate
campaign, including its unresolved move-90 tail.  The half `<8,10,17>` is
a verified quiet ender with Frobenius 39; the thirteen exceptional odd
children are refuted exactly; and the twenty even children close through
the certified nodes `C,G,K,L,R,S`, exact finite P-positions (the child
after 12 falls to 45, after 62 to 25, after 78 to 27), and one deep
native-verified child.  Two further Sicherman/Blok claims were certified
en route as nodes `R={14,16,20,26}` and `S={16,20,30,34,44}`; `S` closes
through both `K` and `R`.

The only hard branch is the even move 58: `{16,20,34,58}` is long (its
half `<8,10,17,29>` has a second end at 9), so no Quiet End shortcut
exists.  Exact native scans refute every odd reply from 3 through 501
except **291**, which wins: `{16,20,34,58,291}` is P with Frobenius 353,
proved by the native recurrence (3,498,711 cumulative states) and
reproduced independently by the Python reference evaluator (3,407,297
states).  The certificate suite verifies the edge's legality and
destination and pins the deep P evaluation in the native test module,
following the same native-finite convention as the g4 candidate rows.

With these rows the certified table answers **every even move from 2
through 24** after opening 16; odd moves lose by Hutchings' theorem.  The
lowest uncertified branch is now the even move 26, where no reply into
the present node set works and Sicherman's list offers no three-generator
`{16,26,x}` claim; the natural candidates are new nodes such as
`{14,16,26}`-derived positions from Blok's 2022 report.  See
`RUN_MOVE_20_ANSWER.txt` and the refreshed certificate totals: 15 nodes,
154 exceptional odd children, 169 even children, 6 pairing edges, 4
published edges, 1 native-finite edge.

### Attempt 7 — the move-26 frontier: `{16,26}` is short and under siege

`{16,26}` appears in no published table: Sicherman's `{m,n}` list stops at
`{15,26}`, and his `{16,20}` row ends mid-bracket.  Yet its divide-by-two
monoid `<8,13>` is a coprime pair, hence a quiet ender with Frobenius 83,
so `{16,26}` is a **short** position: its outcome is decided by finitely
many children — 23 exceptional odd moves and 42 even moves.  If every one
of them is an N-position then 26 is a winning reply to the opening 16 and
the bounty question is answered with `a(16)=2`; if some child is P, that
child answers move 26 and the certified table grows again.  Either way
this is the first bounded reformulation of a live branch of the problem.

Progress so far, all exact:

- **Odd side closed.**  Native scans refute every odd reply through 99
  (covering all 23 exceptional odds; larger odds lie in `<8,13>` and lose
  by the Quiet End Theorem).  The Python reference independently
  reconfirms every exceptional odd through 57, the largest taking
  18,718,660 states; the four largest are native-verified.

- **29 of 42 even children refuted**, through the certified node graph
  (`C,G,K,F,H`) and exact odd replies found by staged native scans, for
  example `18->5`, `40->11`, `62->59`, `72->43`, `140->13`.

- **The pair phenomenon.**  The children after 36 and 56 have *no odd
  refutation at all*: their halves are quiet enders and every exceptional
  odd child is N (native scans; Python reconfirms all 15 for the combined
  node).  They refute **each other**: the new position

  ```text
  {16,26,36,56}   is a P-position,
  ```

  proved by the same short-node discipline — quiet-ender half
  `<8,13,18,28>` with Frobenius 51, fifteen exceptional odd children all
  N (Python re-verified), and all 26 even children refuted, the last
  being the deep long child after 102, where the odd reply **201** wins
  (`{16,26,36,56,102,201}` is P with Frobenius 287, 27,865,056 states).
  This position is on no published list.  Consequently the `{16,26}`
  children 36 and 56 are both N, answered by one another.

- **Remaining open children of `{16,26}`:** 60, 70, 82, 86, 88, 92, 98,
  114, 118, 124, 134, 150, 166.  Eleven have partial odd scans that
  simply need finishing; 60 has resisted through 303; and 88 is a third
  odd-complete candidate whose even children interlock with the pair
  (`<16,26,88,36>=<16,26,36>` and `<16,26,88,56>=<16,26,56>`, both now
  known N, so 88's refutation, if any, lies among its other children).

The gcd-four candidate work also surfaced a cautionary correction kept in
Attempt 6: `{16,20,34,58}` fell to the odd reply 291 only after 124 exact
refusals, and here `{16,26,36,56,102}` fell at 201 after 149 — deep odd
winners are the norm on this frontier, exactly as Blok's "nearly short"
heuristic predicts.

### Attempt 8 — the U subtree falls to a single boundary position

The second campaign wave certified the pair position `V={16,26,36,56}`
as a repository node (16 nodes, 179 exceptional odd children, 195 even
children, 11 native-finite edges) and drove the decisive odd-complete
child 88 nearly to closure.  `U={16,26,88}` has a verified quiet-ender
half with Frobenius 75, all 21 exceptional odd children refuted, and 36
of 38 even children answered — through the certified graph, through nine
absorption rows that inherit sibling refutations, through the pair rows
`36->56` and `56->36` into `V`, and through sixteen new exact odd
winners, the deepest being `{16,26,38,88,371}` (Frobenius 469;
63,240,955 cumulative states).  Python reproductions with exactly
matching state counts confirm every destination that fit a batch budget,
including two above 57 million states.

The two remaining children collapse into one another: `98 = 16+82`, so
`<16,26,88,98,82> = <16,26,82,88> = X` exactly.  Consequently

```text
U is N  <=>  X is P,
```

and either branch resolves both stubborn children at once.  `X` is long
(its half `<8,13,41,44>` has a second end), exact scans refute every odd
reply through 407 with no translation pattern in the 200 recorded
winning responses, and a single further candidate at this depth costs
about 80 CPU-minutes and 50 GB.  The campaign therefore ends where the
`{16,20,28,90}` tail ended: at a long position whose classification
needs Sicherman's ultimate-periodicity method (the tool that settled
`{8,10,22}`), not more linear scanning.  `RUN_MOVE_26_U_SUBTREE.txt`
preserves the exact state, including the ready sub-node
`W={16,26,62,98}` (odd side fully clean) for the U-P world.

### Sources

- <https://math.colgate.edu/~integers/yg2/yg2.pdf>
- Thomas Blok, *Sylver Coinage positions with g=2* (2021):
  <https://sicherman.net/sylver/Sylver_Coinage_positions_with_g=2.pdf>
- Thomas Blok, *Sylver Coinage even positions in 14* (2022):
  <https://sicherman.net/sylver/Sylver_Coinage_even_positions_in_14.pdf>
- George Sicherman, *Some P-Positions With g>1*:
  <https://sicherman.net/sylver/ppos.html>

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
