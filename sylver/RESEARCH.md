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

### Attempt 9 — the ultimate-periodicity engine is operational

The missing gcd-two tail tool now exists in two independently exercised
forms.  `periodicity.py` is an executable specification of the Periodicity
Theorem recurrence, and `periodicity_engine.cpp` is its checkpointed native
campaign implementation.  If `f` is the Frobenius number of the divide-by-two
even part and `tbar=2f`, every translated state is an even oversemigroup plus
a bounded set of odd-anchor offsets.  Odd replies below the window reset to a
single anchor and are summarized by a monotone P-hit flag; replies above the
window are generated.  Exact full-window snapshots, taken only after every
flag is stable, are compared with Brent's algorithm.  A match is an equality
of bit-packed states, not a hash collision.

Three differential controls cross the translated threshold and agree with
the independent finite solver.  Both implementations certify periods
`(start,length)=(9,4)` for `{4,6}`, `(57,4)` for `{6,16}` (whose P child is
7), and `(49,8)` for the published long P-position `{8,10,22}`.  The latter
uses 50 shapes and also passes an AddressSanitizer/UndefinedBehaviorSanitizer
run.  The native tests load all 203 exact `X+x` campaign rows through 407 and
confirm that external cached rows cannot trigger a premature period.

For `X`, the engine reuses each recorded N row and its exact P-destination,
then reconstructs the first genuinely new translated row at 409.  The first
ten lower-window dependencies are now independently checkpointed N:

```text
{16,26,55,82,88,173}   F=157     4,045,437 states
{16,26,71,82,88,173}   F=163    26,701,579 states
{16,26,81,82,88,173}   F=183    39,023,226 states
{16,26,82,87,88,173}   F=179     1,129,858 states
{16,26,82,88,97,173}   F=183    57,242,953 states
{16,26,82,88,101,173}  F=219    50,185,744 states
{16,26,82,88,103,173}  F=195    49,349,028 states
{16,26,82,88,107,173}  F=209    68,120,815 states
{16,26,82,88,111,173}  F=229     8,560,698 states
{16,26,82,88,113,173}  F=185    43,850,109 states
```

The eleventh dependency `{16,26,82,88,117,173}` has Frobenius 235 and is the
frontier of this initial checkpoint.  These are exact advances inside the
periodic recurrence, but they do **not** yet decide `X+409`, much less `X`,
`U`, move 26, or the opening.  See `RUN_PERIODICITY_ENGINE.txt`; the
resumable cache is `move26_data/periodicity_x.cache`.

### Attempt 10 — 16-hour dependency-closure campaign

The first long continuation exposed a performance bug rather than a
mathematical obstruction.  It added 702 exact outcomes but then spent more
than six hours reconstructing the same row-409 subproblems while a small
ring cache evicted them.  It was stopped after 12:11:16 at 5,336,600 KB peak
RSS.  A no-memo diagnostic reproduced the failure mode: 150 million
evaluation calls in 3:55 while reaching only 225 shapes and eight even
parts.  The engine now prunes children whose reset flag already decides
them, memoizes every `(shape,row)` result for the lifetime of the active row,
writes the exact cache by atomic rename, and reports dependency-closure
progress.  The row memo is cleared at every row boundary, so it does not
alter the finite-state recurrence or become part of a period certificate.

The corrected validation pass completed 10,244 exact fallbacks in 10:23 with
a 97,104 KB peak and no disagreement with the 1,070-entry inherited cache.
The promoted continuation then ran for 3:44:00 at 99% CPU with a 1,325,608 KB
peak.  It completed another 7,185 exact positions; at its 7,000-result marker
it had evaluated 4,072,029,617 finite-solver states.  The final cache has
18,499 distinct positions, comprising 17,494 N and 1,005 P positions, with
no duplicate keys or conflicting outcomes.  Relative to the normalized
368-position imported seed, the campaign contributed 18,131 exact outcomes
(17,281 N and 850 P).  High-Frobenius internal P-positions as well as N
positions occur in the cache; neither outcome is being inferred from search
time or a finite prefix.

The optimization is independently guarded by the same six differential
periodicity tests, including the published `{8,10,22}` certificate, and all
19 finite-solver regression tests.  Representative cache entries were also
recomputed with the standalone native solver with exactly matching outcomes
and state counts.  Nevertheless the closure still did **not** finish
`X+409`, emit a `P-HIT`, or repeat a stable full snapshot.  Thus `X`, `U`,
move 26, and opening 16 remain undecided.  The concrete advance is a much
faster, bounded-memory exact engine and a cache nearly fifty times the
normalized starting size.  Resume row 409 from this cache; do not restart
the direct odd scan.  `RUN_PERIODICITY_16H.txt` contains the phase timings,
fingerprints, validation commands, and exact final counts.

### Attempt 11 — 24-hour row-409 continuation

The corrected engine was continued from the audited 18,499-position cache
for a fixed 23:40:00 process budget, leaving time for shutdown, verification,
and documentation.  It ran at 99% CPU with a 1,280,684 KB peak and no swaps,
registered at least 60,000 translated shapes and 304 even parts, and completed
43,004 additional finite fallbacks.  The final exact cache has 61,503 distinct
positions: 57,641 N and 3,862 P, with no duplicate keys, conflicting outcomes,
malformed rows, or bad values.  The last aggregate marker reports
29,006,854,338 finite-solver states at 43,000 additions; four further exact
outcomes were saved before the configured timeout.

The continuation crossed several coherent hard families exactly.  In
particular `{16,26,38,50,60,k}` is N for every odd `k` from 109 through 119;
the six searches required between 6.47 and 7.37 million states each.  Internal
P-positions likewise grew by 2,857, so the engine is not treating long search
time or a finite prefix as an outcome.  The final cache fingerprint is
`c608b37cd54cf7378d87918971c58fa91d23de15a65521976736ccfd55ee9fc1`.

The run nevertheless emitted no `P-HIT`, `PERIOD`, or completed `X+409`
classification; `scanned_to` remained 407 and the key `{16,26,82,88,409}` is
absent.  Thus `X`, `U`, move 26, and opening 16 remain undecided.  Both the six
periodicity controls and all 19 finite-solver regressions pass after the run,
and an O3 rebuild is bit-for-bit identical to the campaign executable.

Resume row 409 from the enlarged cache rather than restarting the direct odd
scan.  Since the next restart must reconstruct at least 60,000 shapes, the
most promising engineering improvement is a proof-safe active-row checkpoint
if replay begins to dominate: shape/even-part tables, transitions, ring
stamps, reset flags, and the row memo must be serialized together.  See
`RUN_PERIODICITY_24H.txt` for the command, every aggregate milestone, resource
record, fingerprints, exact audit, and verification.

### Attempt 12 — proof-safe active-row restart

The row-409 replay risk identified by Attempt 11 is now removed.  The native
engine writes a versioned binary `.rowstate` when `SIGINT` or `SIGTERM` is
received, using a temporary file plus atomic rename.  The checkpoint includes
the complete active recurrence state: even parts and fill edges, shapes and
materialized transitions, ring values and stamps, singleton histories and
reset flags, the active-row memo, P-hits, exact-work counters, and the exact
cache entries on which those values depend.  Resume requires the current
exact cache to contain that dependency set with identical outcomes.  A
64-bit checksum and structural validation reject truncation, corruption,
wrong generators, invalid graph references, and incompatible frontiers.

Signals are only flags inside the handler.  The embedded finite solver polls
at recurrence boundaries and unwinds normally, so a partially searched exact
subgame is discarded while every completed fallback remains in the atomic
text cache.  The active row is then saved at a safe C++ boundary.  On resume,
the engine re-sweeps that row from its first shape; restored memo entries make
completed calls cheap and the normal backfill loop catches a child registered
immediately before interruption.  The local Brent candidate is deliberately
reset rather than trusted across a restart.  This can delay a certificate but
cannot create a false repeated snapshot.

A deterministic test interrupts the published `{8,10,22}` control after 25
evaluation calls, rejects a checksum-corrupted checkpoint, reloads the intact
state, and recovers the exact 8-cycle with 50 shapes and no P-hit.  The same
mechanism was exercised twice on a temporary copy of the real 61,503-entry
`X` cache: the first stop saved row 409 at 1,000 evaluations with 207 shapes
and four even parts; the second loaded it and advanced to 2,000 evaluations,
214 shapes, and six even parts.  The phases took 0.08 and 0.07 seconds, and
the second checkpoint was 2,375,024 bytes.  A separate real `SIGTERM` test
exited 143 after atomically saving a loadable row checkpoint.  These bounded
tests do not add an outcome or classify `X+409`; the audited exact cache is
unchanged.
See `RUN_PERIODICITY_CHECKPOINT.txt` for format, commands, fingerprints, and
verification.

### Attempt 13 — 24-hour proof-safe row-409 continuation

The first real campaign using the active-row checkpoint ran for the fixed
23:40:02 wall-clock budget from the audited 61,503-position cache.  It added
17,602 conflict-free exact outcomes (16,418 N and 1,184 P), leaving 79,105
distinct positions: 74,059 N and 5,046 P.  The last aggregate marker records
25,212,605,176 finite-solver states at 17,000 additions; another 602 completed
outcomes were atomically saved afterward.  The cache contains no malformed
row, duplicate key, or conflicting outcome.

The active row expanded from a cold restart to 88,003 translated shapes and
330 even parts while `scanned_to` remained 407.  The configured `SIGINT` then
flushed the exact cache and atomically saved row 409 at 8,824,393 evaluation
calls.  The 196,330,507-byte version-1 rowstate has SHA-256
`8c0c2551dd6f26b23bce001db235535ddb556b74880b4d85d878a5f8e93251cc`;
the corresponding exact cache has SHA-256
`04343b1746feeaa93614026e3be6c3599c90587bd38b7cd0705b5ff34cfd28f6`.
Peak RSS was 884,576 KB with no swaps.

The campaign emitted no `P-HIT`, `PERIOD`, or `LIMIT-REACHED`, and neither
`{16,26,82,88}` nor `{16,26,82,88,409}` appears in the cache.  Thus this is a
substantial exact frontier advance, not a classification of `X`, `U`, move
26, or opening 16.  The checkpoint itself was audited on private copies: the
engine loaded all 88,003 shapes and the exact dependency set, advanced from
evaluation 8,824,393 to 8,824,394, and saved a new checkpoint in 4.11 seconds.
The repository artifacts retained their hashes.  All seven periodicity tests,
all 19 finite-solver tests, both warning-clean optimized builds, byte
compilation, and `git diff --check` pass.

The next exact continuation should use this cache and its default `.rowstate`
with the same two base records.  That resumes row 409 rather than rebuilding
the 88,003-shape graph.  It must still require an actual P-hit or an exact
repeated stable full snapshot.  See `RUN_PERIODICITY_48H.txt` for every
aggregate marker, command, fingerprint, cache audit, resource record, and
resume verification.

### Attempt 14 — saved-frontier continuation past 100,000 shapes

The saved row-409 frontier then supported another fixed 23:40:02 campaign,
this time without rebuilding the 88,003 shapes already known.  Startup loaded
the prior 196 MB rowstate at 8,824,393 evaluation calls.  The continuation
added 11,473 unique, conflict-free exact outcomes (10,848 N and 625 P), so the
cache now contains 90,578 positions: 84,907 N and 5,671 P.  The restored
aggregate counter reached 29,000 completed outcomes and 51,009,297,456
finite-solver states at cache entry 90,503; another 75 outcomes were saved
afterward, and their state counts are not estimated.

The active graph grew by 14,802 shapes and 17 even parts.  At the configured
interrupt the engine flushed the cache and atomically saved row 409 with
`scanned_to=407`, 102,805 shapes, 347 even parts, and 10,376,913 evaluation
calls.  The 229,278,530-byte rowstate has SHA-256
`2548df87bdca4c414d86bf0b8e566b5757dc0dacdd926a49c74a5e674832690d`;
the corresponding cache has SHA-256
`060be51b92d1921d7dd89f0e29783b040bac8b7c560e919c611556c7aac7be1a`.
Peak RSS was 983,940 KB, with no swaps or major page faults.

The campaign again emitted no `P-HIT`, `PERIOD`, `LIMIT-REACHED`, or
completed row.  Neither `{16,26,82,88}` nor `{16,26,82,88,409}` is cached, so
the new finite frontier still does not classify `X`, `U`, move 26, or the
opening.  On an isolated copy, the final checkpoint loaded all 102,805 shapes
and advanced exactly from evaluation 10,376,913 to 10,376,914 before saving
and exiting with the expected status 75.  The authoritative artifact hashes
were unchanged.  All seven periodicity tests, all 19 finite-solver tests,
byte compilation, both warning-clean optimized builds, binary reproduction,
an ASan+UBSan interrupt/resume control, the cache audit, and
`git diff --check` pass.

Any further exact continuation should resume this rowstate rather than
rebuild it or restart the exhausted direct odd scan.  Mathematical success
still requires an actual P-hit or an exact repeated stable full snapshot.
See `RUN_PERIODICITY_72H.txt` for the full command, cumulative-counter
semantics, every marker, fingerprints, audit, resource record, and resume
verification.

### Attempt 15 — checkpoint continuation past 110,000 shapes

The next fixed 23:40:03 campaign resumed the audited 229 MB rowstate at
102,805 shapes and 10,376,913 evaluation calls.  It added 8,723 unique,
conflict-free exact outcomes (8,321 N and 402 P), bringing the cache to
99,301 positions: 93,228 N and 6,073 P.  The restored aggregate counter
reached 37,000 completed outcomes and 73,121,625,852 finite-solver states at
cache entry 98,503.  Another 798 completed outcomes were saved afterward;
their solver-state counts are not estimated.

The active graph grew by 9,321 shapes and one even part.  At the configured
interrupt the engine flushed the cache and atomically saved row 409 with
`scanned_to=407`, 112,126 shapes, 348 even parts, and 10,952,024 evaluation
calls.  The 250,115,604-byte rowstate has SHA-256
`13a83425079606f2f6f1255f15788b1fd92f4044d76f39cad89a4ecbbcf30111`;
the corresponding cache has SHA-256
`4b01e2a7bd1ddaa827d03352ea71c9d7692d7d44e2a47b58837db7b59fb96762`.
Peak RSS was 1,019,940 KB with no swaps.

The campaign again emitted no `P-HIT`, `PERIOD`, `LIMIT-REACHED`, error, or
completed row.  Neither `{16,26,82,88}` nor `{16,26,82,88,409}` is cached, so
the finite frontier still does not classify `X`, `U`, move 26, or the
opening.  On an isolated copy, the final checkpoint loaded all 112,126 shapes
and advanced exactly from evaluation 10,952,024 to 10,952,025 before saving
and exiting with the expected status 75.  The authoritative artifact hashes
were unchanged.  All seven periodicity tests, all 19 finite-solver tests,
byte compilation, both warning-clean optimized builds, binary reproduction,
an ASan+UBSan interrupt/resume control, the cache audit, and
`git diff --check` pass.

Any further exact continuation should resume this rowstate rather than
rebuild it or restart the exhausted direct odd scan.  Mathematical success
still requires an actual P-hit or an exact repeated stable full snapshot.
See `RUN_PERIODICITY_96H.txt` for the full command, cumulative-counter
semantics, every marker, fingerprints, audit, resource record, and resume
verification.

### Attempt 16 — checkpoint continuation to 117,895 shapes

The next fixed 23:40:02 campaign resumed the audited 250 MB rowstate at
112,126 shapes and 10,952,024 evaluation calls.  It added 7,752 unique,
conflict-free exact outcomes (7,287 N and 465 P), bringing the cache to
107,053 positions: 100,515 N and 6,538 P.  The restored aggregate counter
reached 45,000 completed outcomes and 96,881,574,791 finite-solver states at
cache entry 106,503.  Another 550 completed outcomes were saved afterward;
their solver-state counts are not reconstructed or estimated.

The active graph grew by 5,769 shapes and one even part.  At the configured
interrupt the engine flushed the cache and atomically saved row 409 with
`scanned_to=407`, 117,895 shapes, 349 even parts, and 12,843,850 evaluation
calls.  The 267,852,422-byte rowstate has SHA-256
`ddfc71bf8a3e841371bf89f6fd1de8d6eb0a6045f2b64599277f097027554bb4`;
the corresponding cache has SHA-256
`e5fdb8365cc32c5d3500f5e26eddd8180396566dfc2994aeaf7babf72a07b971`.
Peak RSS was 1,178,784 KB with no swaps or major page faults.

The campaign again emitted no `P-HIT`, `PERIOD`, `LIMIT-REACHED`, error, or
completed row.  Neither `{16,26,82,88}` nor `{16,26,82,88,409}` is cached, so
the finite frontier still does not classify `X`, `U`, move 26, or the
opening.  On an isolated copy, the final checkpoint loaded all 117,895 shapes
and advanced exactly from evaluation 12,843,850 to 12,843,851 before saving
and exiting with the expected status 75.  The authoritative artifact hashes
were unchanged.  All seven periodicity tests, all 19 finite-solver tests,
byte compilation, both warning-clean optimized builds, binary reproduction,
an ASan+UBSan interrupt/resume control, the cache audit, and
`git diff --check` pass.

Any further exact continuation should resume this rowstate rather than
rebuild it or restart the exhausted direct odd scan.  Mathematical success
still requires an actual P-hit or an exact repeated stable full snapshot.
See `RUN_PERIODICITY_120H.txt` for the full command, cumulative-counter
semantics, every marker, verbose exact completions, fingerprints, audit,
resource record, and resume verification.

### Attempt 17 — five-day checkpoint continuation to 149,895 shapes

The audited 117,895-shape rowstate supported a fixed 119:40:09 continuation.
It added 32,390 unique, conflict-free exact outcomes (30,722 N and 1,668 P),
bringing the cache to 139,443 positions: 131,237 N and 8,206 P.  The restored
aggregate counter reached 77,000 completed outcomes and 211,379,174,929
finite-solver states at cache entry 138,503.  Another 940 outcomes were saved
after that marker; their state counts are not reconstructed or estimated.

The active graph grew by exactly 32,000 shapes and 33 even parts.  At the
configured interrupt the engine flushed the cache and atomically saved row
409 with `scanned_to=407`, 149,895 shapes, 382 even parts, and 16,212,095
evaluation calls.  The 341,480,295-byte rowstate has SHA-256
`4564c217ed2858d9ad3d41fdc3d4b6b04d1e1387fe6c4439a9bf85837030b39a`;
the corresponding cache has SHA-256
`b14ce9cf9af4a9963856cd378778acddcdccc3ca4f162e7c91e46cfb9e030650`.
Peak RSS was 1,482,608 KB with no swaps.

The campaign again emitted no `P-HIT`, `PERIOD`, `LIMIT-REACHED`, error, or
completed row.  Neither `{16,26,82,88}` nor `{16,26,82,88,409}` is cached, so
the finite frontier still does not classify `X`, `U`, move 26, or the
opening.  On an isolated copy, the final checkpoint loaded all 149,895 shapes
and advanced exactly from evaluation 16,212,095 to 16,212,096 before saving
and exiting with the expected status 75.  The authoritative artifact hashes
were unchanged.  All seven periodicity tests, all 19 finite-solver tests,
byte compilation, both warning-clean optimized builds, binary reproduction,
an ASan+UBSan interrupt/resume control, the cache audit, and
`git diff --check` pass.

Any further exact continuation should resume this rowstate rather than
rebuild it or restart the exhausted direct odd scan.  Mathematical success
still requires an actual P-hit or an exact repeated stable full snapshot.
See `RUN_PERIODICITY_240H.txt` for the full command, every aggregate marker,
fingerprints, audit, resource record, and resume verification.

### Attempt 18 — second five-day continuation to 198,492 shapes

The audited 149,895-shape rowstate supported another fixed 119:40:12
continuation.  It added 51,993 unique, conflict-free exact outcomes (48,749 N
and 3,244 P), bringing the cache to 191,436 positions: 179,986 N and 11,450
P.  The restored aggregate counter reached 129,000 completed outcomes and
334,077,713,961 finite-solver states at its last marker.  Another 933 outcomes
were saved afterward; their state counts are not reconstructed or estimated.

The active graph grew by 48,597 shapes and 53 even parts.  At the configured
interrupt the engine flushed the cache and atomically saved row 409 with
`scanned_to=407`, 198,492 shapes, 435 even parts, and 19,379,294 evaluation
calls.  The 452,049,815-byte rowstate has SHA-256
`c1e6c637f4bc2e8042c7c82a24db31362b951c9b13a9bcbc074f08dfcfd1db55`;
the corresponding cache has SHA-256
`5eb6b4e6d30e754cbef158e89646fce1f8e82b1ccade1fc1347cf9bc1ad73cd8`.
Peak RSS was 1,620,844 KB, with no swaps.

The campaign again emitted no `P-HIT`, `PERIOD`, `LIMIT-REACHED`, error, or
completed row.  Neither `{16,26,82,88}` nor `{16,26,82,88,409}` is cached, so
the finite frontier still does not classify `X`, `U`, move 26, or the
opening.  On an isolated copy, the final checkpoint loaded all 198,492 shapes
and advanced exactly from evaluation 19,379,294 to 19,379,295 before saving
and exiting with the expected status 75.  The authoritative artifact hashes
were unchanged.  All seven periodicity tests, all 19 finite-solver tests,
byte compilation, both warning-clean optimized builds, binary reproduction,
an ASan+UBSan interrupt/resume control, the cache audit, and
`git diff --check` pass.

Any further exact continuation should resume this rowstate rather than
rebuild it or restart the exhausted direct odd scan.  Mathematical success
still requires an actual P-hit or an exact repeated stable full snapshot.
See `RUN_PERIODICITY_360H.txt` for the full command, every aggregate marker,
fingerprints, audit, resource record, and resume verification.

### Attempt 19 — third five-day continuation to 220,574 shapes

The audited 198,492-shape rowstate supported a fixed 119:40:00 continuation.
It added 24,815 unique, conflict-free exact outcomes (23,322 N and 1,493 P),
bringing the cache to 216,251 positions: 203,308 N and 12,943 P.  The
restored aggregate counter reached 154,000 completed outcomes and
448,043,124,906 finite-solver states at its last marker.  Another 748 outcomes
were saved afterward; their state counts are not reconstructed or estimated.

The active graph grew by 22,082 shapes and 12 even parts.  At the configured
interrupt the engine flushed the cache and atomically saved row 409 with
`scanned_to=407`, 220,574 shapes, 447 even parts, and 22,641,268 evaluation
calls.  The 504,832,835-byte rowstate has SHA-256
`cd2a912587395e221d4956236db365f74a2c474d855c2d28d0e45551008a1c28`;
the corresponding cache has SHA-256
`15886b3181560e5c1d515860bdb8e95678569b37c16fa32d74dd57af37e169a1`.
The last full resource audit retained a 1,650,760 KB high-water RSS.  The
outer GNU-time wrapper was lost during monitoring while its timeout and
worker survived, so no final time-wrapper record is claimed; process elapsed
heartbeats and the surviving 7180-minute timeout certify the compute window.

The campaign again emitted no `P-HIT`, `PERIOD`, `LIMIT-REACHED`, error, or
completed row.  Neither `{16,26,82,88}` nor `{16,26,82,88,409}` is cached, so
the finite frontier still does not classify `X`, `U`, move 26, or the
opening.  On an isolated copy, the final checkpoint loaded all 220,574 shapes
and advanced exactly from evaluation 22,641,268 to 22,641,269 before saving
and exiting with the expected status 75 in 8.00 seconds.  The authoritative
artifact hashes were unchanged.  All seven periodicity tests, all 19 finite-
solver tests, byte compilation, both warning-clean optimized builds, binary
reproduction, an ASan+UBSan interrupt/resume control, the cache audit, and
`git diff --check` pass.

Any further exact continuation should resume this rowstate rather than
rebuild it or restart the exhausted direct odd scan.  Mathematical success
still requires an actual P-hit or an exact repeated stable full snapshot.
See `RUN_PERIODICITY_480H.txt` for the full command, every aggregate marker,
fingerprints, audit, resource-record caveat, and resume verification.

### Attempt 20 — the even flank of X falls in one hour

Every campaign against `X={16,26,82,88}` had attacked its odd side: 203
exact odd refutations through 407, then ~480 hours of single-threaded
periodicity grinding on the tail.  `X`'s **even** children — exactly 32,
one per gap of the half `<8,13,41,44>` — had never been examined, even
though any even P child would prove `X` N and answer move 26 by 88, and
every even N child is a mandatory ingredient of an eventual `X`-is-P
certificate.

Three tools closed the flank.  `native_solver.cpp` gained a root-level
hint pass (an outcome-invariant reordering: a hinted candidate that wins
is returned at once, otherwise the unmodified exhaustive loop decides)
and an explicit `--odd-list` mode so quiet-ender children scan only
their exceptional odds.  `parallel_solve.py` runs scan jobs across ten
worker processes with the audited cache row format, atomic writes, and
conflict detection.  `x_even_flank.py` routes children through exact
minimal-generator identities before any search: an odd or even reply
whose destination already lies in the audited periodicity cache or the
certified node graph refutes the child for free.

The routing pass alone refuted **26 of 32** children in seconds — the
480-hour periodicity investment recycled directly, since its dependency
closure had already classified thousands of positions of the form
`{16,26,82,88,+anchors}` that nobody had queried as refutations.  The
six survivors (44, 46, 66, 70, 76, 86) are all long positions, so no
Quiet End pruning was applied; bounded parallel sorties over odd replies
3..201 refuted every one, the deepest being
`{16,26,82,86,88,105}` (Frobenius 197; 58,090,730 states).  Python
reproductions match exactly for the three destinations inside the batch
budget; all six were rerun standalone in the 8- and 16-word builds with
bit-for-bit agreement.  The 569 scan rows and six new P-positions (none
on any published list) were merged into the exact cache with zero
conflicts (216,251 -> 216,967 rows).  See `RUN_X_EVEN_FLANK.txt`.

**Consequence.**  Every even child of `X` is N, and every odd child
through 407 is N.  If `X` is N at all, its winning reply is an odd move
of at least 409 — precisely the question the periodicity engine's row
frontier addresses.  The even half of any `X`-is-P certificate is now
complete and audited.  `X`, `U`, move 26, and the opening remain
undecided; the engine campaign should resume from the saved 220,574-
shape rowstate, now with the flank rows in its cache and with the
parallel-fallback and hint machinery of this attempt available for its
next upgrade.

### Attempt 21 — the parallel engine measures the row-409 mountain

The engine gained batch-parallel exact fallbacks behind
`--exact-threads`: the row sweep collects base-region cache misses
instead of solving them inline, solves each batch on a worker pool of
independent embedded solvers, and re-sweeps with a warm memo.  Unknown
values never reach the ring, row memo, `first_p`, or a snapshot, so the
period certificate remains a function of exact outcomes only; with one
thread the engine is unchanged.  Three ~7-hour launches against the
saved row-409 frontier then taught three lessons, each caught by the
monitoring-and-audit discipline rather than by luck
(`RUN_PERIODICITY_500H.txt`).

First, unmemoized unknowns livelock: without a transient per-sweep
unknown-memo the first sweep re-derived the same pending region for
12.5 billion evaluations.  Second, batching after a complete sweep is
too late: expansion outran memory, so batches now trigger at a pending
threshold, letting resolved P outcomes prune sibling expansion through
the `first_p` reset flags while the closure is still being discovered.
Third — the soundness finding — `ensure_single_history` discarded
`evaluate`'s return value, so a collect-mode unknown could silently
mark a singleton history complete and corrupt a reset flag that
outcomes depend on.  The parallel rowstates were therefore discarded
and the campaign state rolled back to the audited 480-hour serial
checkpoint (`cd2a9125…`); the fix stops history advancement at an
unknown and defers the dependent child.  Nineteen incidental exact
rows survived (solved inline with collect off; two independently
re-verified) and the cache stands at 216,986 conflict-free rows.

The block's deliverable is the measurement.  Row `X+409`'s dependency
closure exceeds **3.15 million translated shapes** and **12.5 million
distinct base-region exact positions**, unsaturated at a 45 GB memory
guard — at least 15x beyond everything 480 hours of serial grinding
reached, and the first quantification of why that siege never finished
the row.  During expansion the recycled cache absorbs nearly all exact
demand: on this machine the binding constraint is memory for the shape
graph, not CPU.  Completing row 409 by brute closure needs order 10^7
exact solves and a graph beyond 62 GB as presently represented.  The
odd tail of `X` is now known to be guarded by a genuinely enormous
finite computation; the next investment decision (compact the
representation, attack the other eleven open children of `{16,26}`
directly, or put the measurement in front of the two other people who
work this exact frontier) is recorded in the dashboards.

### Attempt 22 — the sibling flank holds: recycling, then the same wall

The eleven other open even children of `{16,26}` were attacked head-on,
since any P child among them answers move 26 without deciding `X`.
The recycling pass paid first, as it has all campaign: every historical
scan artifact was banked into the audited cache with per-row Frobenius
re-validation (2,373 outcomes, zero conflicts; `sylver/scan_records.py`),
refuting child 134 outright by the banked reply 89, and the nine
refutations that existed only as prose in `RUN_MOVE_26_FRONTIER.txt`
were re-derived exactly (all P, largest 48 million states) and banked.

The sortie itself (`sylver/children_sortie.py`, depth-interleaved
chunks over uncached odd replies, per-worker memory rlimits) added 249
exact rows across two launches and found **no P child**: every scanned
reply to every child is N, with contiguous refuted frontiers from 87
(child 124) to 191 (child 60).  Beyond them, single positions carry
Frobenius numbers in the 300s-500s and memos past 10 GB — the same
wall as `X` at 407 and `{12,16,20}` at 409.  See
`RUN_CHILDREN_SORTIE.txt`.

The strategic picture is now sharp.  `{16,26}`'s classification rests
on twelve long children; every cheap flank (even replies, recycling,
absorption, shallow odd scans) is exhausted; and each remaining branch
is guarded by a computation of the measured row-409 class.  The three
live options are a compact shape representation for the periodicity
engine, running the periodicity method on a cheaper child than `X`
(the engine accepts any gcd-2 base; a child with a smaller half
Frobenius has a smaller translated state space), or placing the seven
unpublished P-positions, the certified table, and the closure
measurement before Sicherman and Blok.

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
