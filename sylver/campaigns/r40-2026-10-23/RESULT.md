# Reply 40 after the opening 16: twenty-six answers fail

After the opening 16, the lowest reply without a certified answer is 38, and
by search 72 answers it
([reply-38 record](../r38-2026-10-09/RESULT.md#the-search-for-an-answer-to-38)).
The next reply, **40, has no known answer**. {16,40} has gcd eight (it is
8·{2,5}), and the Quiet End tools here cover gcd two. So no finite list of
obligations bounds the answers to 40: any legal move may answer it.

This record certifies three P-positions:
- **Q={16,20,46}**. Its half is {8,10,23}, the half's Frobenius number is
  45, and Q has 39 obligations. Q is on George Sicherman's
  [list of P-positions](https://sicherman.net/sylver/ppos.html) (last
  updated September 28), so this is an independent confirmation.
- **B58={16,36,40,58}**. Its half is {8,18,20,29}, the half's Frobenius
  number is 59, and B58 has 51 obligations. B58 is not on Sicherman's list.
- **B78={16,36,40,78}**. Its half is {8,18,20,39}, the half's Frobenius
  number is 69, and B78 has 61 obligations. B78 is not on Sicherman's list
  either.

With them, the audit refutes twenty-six answers to 40:

| Answer a | {16,40,a} | Move | Reaches | Known P by |
| ---: | --- | ---: | --- | --- |
| 2 | {2} | 3 | {2,3} | finite witness |
| 4 | {4} | 6 | C={4,6} | certified node |
| 6 | {6,16} | 4 | C | certified node |
| 8 | {8} | 14 | E={8,14} | certified node |
| 10 | {10,16} | 9 | {9,10,16} | finite witness |
| 12 | {12,16} | 14 | F={12,14,16} | certified node |
| 14 | {14,16,40} | 8 | E | certified node |
| 18 | {16,18,40} | 5 | {5,16,18} | finite witness |
| 20 | {16,20} | 34 | T={16,20,34} | certified node |
| 22 | {16,22,40} | 12 | P0={12,16,22} | certified node |
| 24 | {16,24} | 10 | K={10,16,24} | certified node |
| 26 | {16,26,40} | 11 | {11,16,26,40} | finite witness |
| 28 | {16,28,40} | 38 | B28={16,28,38,40} | the [reply-38 record](../r38-2026-10-09/RESULT.md) (its audit, run here) |
| 30 | {16,30,40} | 17 | {16,17,30,40} | finite witness |
| 34 | {16,34,40} | 20 | T | certified node |
| 36 | {16,36,40} | 58 | B58 | here |
| 38 | {16,38,40} | 28 | B28 | the reply-38 record |
| 42 | {16,40,42} | 23 | {16,23,40,42} | finite witness |
| 44 | {16,40,44} | 30 | Z′={16,30,40,44} | the [Z record](../z-2026-10-08/RESULT.md) (its audit, run here) |
| 46 | {16,40,46} | 20 | Q | here |
| 50 | {16,40,50} | 11 | {11,16,40,50} | finite witness |
| 58 | {16,40,58} | 36 | B58 | here |
| 70 | {16,40,70} | 37 | {16,37,40,70} | finite witness |
| 78 | {16,40,78} | 36 | B78 | here |
| 94 | {16,40,94} | 21 | {16,21,40,94} | finite witness |
| 102 | {16,40,102} | 33 | {16,33,40,102} | finite witness |

16, 32, 40 and 48 are not legal answers. So **every legal even answer up to
50 fails**, and 58, 70, 78, 94 and 102 fail too. By search, 52, 54, 62
and the odd answers 3 to 73 fail as well
([below](#the-search-for-an-answer-to-40)). **40 remains unanswered**, and
opening 16 remains unresolved.

## The certificate

Q, B58 and B78 are short, so each is P exactly when each of its obligations
leads to N. The obligations are the even moves 2g for the gaps g of its
half, and the half's odd gaps above 1. [audit.py](audit.py) lists them
twice, with the arena referee's profile and with an independent coin-sum
count ([audit.json](audit.json)), and accepts:
- for Q, 33 finite witnesses (all 16 odd obligations, and 17 even ones),
  replayed natively and in Python, and 6 certified nodes: moves 4 and 6
  reach C, 8 and 26 reach G, 14 reaches R, and 30 reaches O;
- for B58, 44 finite witnesses (all 21 odd obligations, and 23 even ones),
  replayed the same way, and 7 certified nodes: moves 4 and 6 reach C, 8
  and 14 reach E, 12 reaches F, 22 reaches P0, and 24 reaches K;
- for B78, 53 finite witnesses (all 26 odd obligations, and 27 even ones),
  the same 7 certified nodes as B58, and its move 20, whose reply 46 reaches
  Q, which the audit certifies first. By search, no odd reply up to 601
  wins after 20 (`scan/b78_finite_20.out` and `scan/b78_finite_20b.out`).

Each finite witness is a certificate `<prefix><move>-certificate.json`, in
the schema the campaign records use: prefix `q` for Q's obligations, `b58_`
for B58's, `b78_` for B78's, and `r40_` for the refutations, with parent
{16,40}.
`python -m sylver.verify_finite_reply --python` replayed each from empty
memos with `native_solver.cpp` and the Python reference evaluator
([verification/](verification/)), and both report P with the same state
count; three of B78's were replayed another way (below).
- Q's replays total 4,525,687 states. The largest is its move 42 answered
  by 89, {16,20,42,46,89}, at 1,626,244.
- B58's replays total 517,445,319 states. The largest is its move 118
  answered by 161, {16,36,40,58,118,161}, at 132,607,400; its Python replay
  took 14,941 seconds, about four hours.
- B78's replays total 1,586,171,937 states. Three are above 150 million
  states, the limit this record's `replay.py` sets for the Python evaluator
  here (as the {16,38,72} certification record did; the reply-38 record's
  limit was 175 million): its moves 90, 102 and 86,
  answered by 217, 181 and 135, at 392,105,455, 349,532,359 and 189,187,613.
  Those three were replayed with `native_solver.cpp` and a sequential,
  memo-verified `kunz_solver.cpp` (`--threads 1 --verify-memo`) built from
  the source snapshot the reply-38 audit pins, as the reply-38 record did
  for B56's largest witnesses and the
  [{16,38,72} certification record](../c72-2026-10-18/RESULT.md) for its
  own. The audit
  checks the Kunz receipts with the reply-38 audit's checker. The other 50,
  up to 131,731,309 states (its move 122 answered by 99), were replayed in
  Python. B78's replays ran on October 25, from 04:57 to 15:20.
- The refutations' replays total 68,435,627. The largest is 70's,
  {16,37,40,70}, at 38,439,250.

The audit then checks the twenty-six refutations: each move is legal and
reaches a finite witness, a certified node, Q, B58, B78, B28 or Z′. For B28 and
Z′ it runs the reply-38 and Z records' own audits of those positions.

**Four routes differ from the search's.** The resolver answered Q's move 22
through the reply-38 record's I={16,20,22,24}, and its move 24 through the
node K. Finite replies replace both: 45 and 29. The other node routes stay:
Q's moves 8, 26 and 30 have no odd reply up to 201 that wins. B58's routes
are all the search's. So are B78's, except two: the resolver answered its
move 34 by 8, reaching {8,34,36} on Sicherman's list, and its move 46 by
20, reaching Q; finite replies replace both, 93 and 37. Its move 20 keeps
the route through Q.

**What it rests on.** Like the other records, this one rests on the Quiet
End Theorem. Through the certified nodes, it also rests on these published
positions:
- **Sicherman's {8,10,22}** (the node H), whose P outcome comes from a
  periodicity computation. Q reaches it through G and O, B58 through K,
  B78 through K and Q, and the refutations through K and through T, which
  uses G and K.
- **Blok's pairing family {8,12,8n+2,8n+6}**, at three of its members:
  n=1, {8,10,12,14}, through E and F, for B58, B78 and the refutations;
  n=2, {8,12,18,22}, through P0, for the same; and n=3, {8,12,26,30},
  through G and O for Q (and so for B78) and through T for the refutations.

B28 and Z′ rest on what their records list: the nodes C, E, F, J and P0 for
B28, and C, E and F for Z′.

No mathematical priority claim is made.

## The search for an answer to 40

The search is recorded in [scan/](scan/). Its sweeps ran without
`--verify-memo`, so apart from what the audit checks, this section is
discovery output, not certified.

**Which answers it tried.**
- **a ≡ 2 (mod 4).** These give {16,40,a} gcd two and a short half, so the
  Quiet End Theorem lists the obligations, and the search can show the
  position P.
- **a ≡ 0 (mod 4).** These give gcd four or eight, which the tools here do
  not cover. Some fail anyway, by one move to a known P-position: those in
  the table above (36 among them, by 58 to B58), and 52 (by 54, to B54
  below).
- **Odd answers.** These give finite positions.

**Odd answers.** The ledger's scan tried 3, the one odd gap above 1 of the
reduced pair {2,5}, and it fails. Here, one P-table sweep found that 5
through 33 all fail (3,167,594 P-positions, about a minute). A second found
that 35 through 57 fail too (156,248,856 P-positions). It stopped at its
one-hour limit during 59: it started at 16:41:36 and its log ends at
17:41:37. A third, from 59 with a six-hour limit (October 24, 21:37, to
October 25, 03:37), found that 59 through 73 fail as well (530,988,925
P-positions after 73). Their winning replies are 330, 62, 163, 19, 103, 25,
45 and 78. It stopped at the limit during 75.

**Even answers a ≡ 2 (mod 4).** `screen.py` first looked for an obligation
reaching a known P-position, for every a up to 398. It then swept the odd
obligations of the survivors, stopping at the first P:

| a | Result |
| --- | --- |
| 6, 10, 14, 18, 22, 30, 34, 38 | an obligation reaches a known P-position (as in the table above, except 30, which the screen refuted by 44 to Z′) |
| 26, 42, 50, 62, 70 | an odd obligation reaches a finite P-position: 11, 23, 11, 61, 37 |
| 46, 54, 58 | every odd obligation leads to N |
| 66, 74, 78, 82, 86 | stopped with 3 to 16 odd obligations left: 86 at the cap of 100,000,000 P-positions, the others at the 30-minute limit |
| 94, 102 | an odd obligation reaches a finite P-position: 21, 33 (light sweep, below) |
| the other 76 from 90 to 398 | stopped with 20 to 23 odd obligations classified, out of 47 to 201 (light sweep) |

62's finite witness, {16,40,61,62}, needs 286,533,125 states when solved
alone. A Python replay would need about 43 GiB of this host's 62 GiB, so 62
is refuted by search here. Certifying it would take a native replay and a
sequential Kunz replay instead, as the ledger did for {16,37,62}.

For 46, 54 and 58, the even obligations decide:
- **46.** Its move 20 reaches {16,20,40,46} = Q, since 40 = 20+20. A pair
  search over the even replies of {16,40,46,60}, one of 46's children,
  found Q's 16 odd and 23 even obligations all leading to N. The audit
  checks the same position, with the two finite routes above.
- **54.** 18 of its even children are short. The triage and short-first
  passes settled all but five: its moves 52, 60, 68 and 76 reach positions whose odd
  obligations all lead to N, and 92's sweep stopped early. The first of
  those, **B54={16,40,52,54}**, had all 33 of its even obligations answered
  too. (Its half is {8,20,26,27}, the half's Frobenius number is 65, and it
  has 55 obligations.) So B54 is P by search, and 54 fails. B54 is not on
  Sicherman's list.
  - Its evidence is in `scan/evidence_16-40-52-54.json`: 46 finite
    witnesses, 1,650,024,795 states in all when each is solved alone, and
    nine routes to certified nodes.
  - Three of the witnesses are above 175 million states: its moves 98, 60
    and 78, answered by 175, 229 and 127, at 395,092,803, 365,742,433 and
    219,812,546. Certifying those would need native replays and sequential
    Kunz replays, as the reply-38 record did for B56's largest witnesses.
- **58.** The same way: its moves 36, 44, 60, 68 and 84 reach short
  positions whose odd obligations all lead to N. The first,
  **B58={16,36,40,58}**, had all 30 of its even obligations answered too.
  (Its half is {8,18,20,29}, the half's Frobenius number is 59, and it has
  51 obligations.) The audit certifies B58 ([above](#the-certificate)), so
  58 fails, and 36 with it. B58 is not on Sicherman's list either.
  - Its evidence is in `scan/evidence_16-36-40-58.json`: 44 finite
    witnesses, 517,445,319 states in all when each is solved alone, and
    seven routes to certified nodes. The largest witness is its move 118
    answered by 161, at 132,607,400 states. All are below the 175 million
    states up to which earlier records replayed in Python, so each was
    replayed in Python too, and the audit certifies B58 the way it does Q.
    The replays ran from October 23, 19:27, to October 24, 06:10, two at a
    time within a 22 GiB memory budget.

Each of 46, 54 and 58 thus fell to a short child that is P: the first one
tested, every time.

**66 to 86** (October 23 to 24). For these five the odd sweeps had stopped
early, so the search went to the even side, as for 54 and 58: it resolved
each even obligation whose child is short, and tested each short child
whose odd obligations all lead to N. A child stayed open when none of its
odd replies was found to win and at least one had hit the limit of five
minutes or 100 million P-positions; its sweep gave up once four had. The
table gives the counts as the pass found them. With the known list as it
now stands, one more child is settled: 74's open child {16,40,58,74} plays
36 and reaches B58.

| a | Short children | Resolved | Odd obligations all N | Open | Those children |
| ---: | ---: | ---: | --- | ---: | --- |
| 66 | 23 | 16 | 36, 44, 52, 68 | 3 | none shown P; {16,36,40,66} is N (by 50, to B50 below) |
| 74 | 26 | 16 | 28, 36, 60 | 7 | {16,28,40,74} is N (by 34, to {16,28,34,40} on Sicherman's list); {16,36,40,74} is N (by 58, to B58); {16,40,60,74} not shown P |
| 78 | 28 | 19 | 36 | 8 | **{16,36,40,78} is P**, so 78 fails |
| 82 | 30 | 18 | 44 | 11 | {16,40,44,82} not shown P |
| 86 | 31 | 23 | 36 | 7 | {16,36,40,86} is N (by 50 and 70, to B50 and B70) |

"Not shown P" means the test left even obligations unresolved, even with
the positions found later: three of {16,40,44,66}'s 34,
seven of {16,40,52,66}'s 36, fourteen of {16,40,66,68}'s 40, five of
{16,40,60,74}'s 40 (and five more not tried), and three of
{16,40,44,82}'s 38 (and three more not tried). The last two tests were
stopped by hand once they could no longer succeed.

Four new P-positions came out of the pass, none on Sicherman's list. The
audit has since certified the first; the other three are P by search:
- **B78={16,36,40,78}.** Its half is {8,18,20,39}, the half's Frobenius
  number is 69, and it has 61 obligations: 26 odd and 35 even, all leading
  to N. So 78 fails, and 36 again. Its evidence is in
  `scan/evidence_16-36-40-78.json`, and the audit certifies it
  ([above](#the-certificate)).
- **B50={16,36,40,50}** and **B70={16,36,40,70}**, which two of
  {16,36,40,86}'s obligations reach. Their halves' Frobenius numbers are 55
  and 65, and they have 47 and 57 obligations. So {16,36,40,x} is P for
  x = 50, 58, 70 and 78. These refute 50 and 70 again, and they show that
  the move 36 does not refute 66 or 86.
- **{16,28,40,42}**, found by a search over the even replies of
  {16,28,40,74}'s children. Its half is {8,14,20,21}, the half's Frobenius
  number is 47, and its 40 obligations (16 odd, 24 even) all lead to N. It
  refutes 28 and 42 again.

Below 90, the answers a ≡ 2 (mod 4) still open are 66, 74, 82 and 86. One
position bears on two of them: {16,40,44,66}, 66's child 44, is also
where {16,40,44,82}'s obligation 66 leads. If it is P, 66 fails; if it is
N, {16,40,44,82} may still be P, and then 82 fails. Three of
{16,40,44,66}'s obligations are open, and their children (its moves 36, 90
and 134) are long. A search for even replies from them (October 24, 21:34)
found none: each such reply whose position is short leads to an
N-position, and the others are beyond the method. The obligation 36 is
the obstacle: its child {16,36,40,44,66} has no winning odd reply up to
401 either, so these methods cannot show {16,40,44,66} P.

**90 to 398** (October 25, 06:00 to 12:21). A light sweep of the odd
obligations ran beside B78's replays: for each a, five minutes or
20,000,000 P-positions, with four threads and a 1 GiB N-cache. It found
that 94 fails by 21 and 102 by 33, and the audit certifies both with finite
witnesses: {16,21,40,94} at 1,199,603 states and {16,33,40,102} at
27,971,381, each replayed natively and in Python. Each of the other 76
stopped with 20 to 23 of its odd obligations classified, all N: 110 at the
cap, the rest at the time limit. So no a from 90 to 398 is yet known to
have all its odd obligations lead to N.

No answer to 40 is known.

## Reproduction

```sh
python sylver/campaigns/r40-2026-10-23/audit.py > /tmp/r40-audit.json
python -m sylver.verify_finite_reply --certificate sylver/campaigns/r40-2026-10-23/q42-certificate.json \
    --output /tmp/q42 --python
```
