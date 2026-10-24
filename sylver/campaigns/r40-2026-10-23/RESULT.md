# Reply 40 after the opening 16: thirteen answers fail

After the opening 16, the lowest reply without a certified answer is 38, and
by search 72 answers it
([reply-38 record](../r38-2026-10-09/RESULT.md#the-search-for-an-answer-to-38)).
The next reply, **40, has no known answer**. {16,40} has gcd eight (it is
8·{2,5}), and the Quiet End tools here cover gcd two. So no finite list of
obligations bounds the answers to 40: any legal move may answer it.

This record certifies one P-position, **Q={16,20,46}**, with half {8,10,23},
Frobenius number 45 and 39 obligations. Q is on George Sicherman's
[list of P-positions](https://sicherman.net/sylver/ppos.html) (last updated
September 28), so this is an independent confirmation.

With it, the audit refutes thirteen answers to 40:

| Answer a | Move from {16,40,a} | Reaches | Known P by |
| ---: | ---: | --- | --- |
| 6 | 4 | C={4,6} | certified node |
| 10 | 9 | {9,10,16} | finite witness |
| 14 | 8 | E={8,14} | certified node |
| 18 | 5 | {5,16,18} | finite witness |
| 22 | 12 | P0={12,16,22} | certified node |
| 26 | 11 | {11,16,26,40} | finite witness |
| 30 | 17 | {16,17,30,40} | finite witness |
| 34 | 20 | T={16,20,34} | certified node |
| 38 | 28 | B28={16,28,38,40} | the [reply-38 record](../r38-2026-10-09/RESULT.md) (its audit, run here) |
| 42 | 23 | {16,23,40,42} | finite witness |
| 46 | 20 | Q | here |
| 50 | 11 | {11,16,40,50} | finite witness |
| 70 | 37 | {16,37,40,70} | finite witness |

So every answer a ≡ 2 (mod 4) from 6 to 50 fails, and so does 70. By search,
54, 58 and 62 fail too ([below](#the-search-for-an-answer-to-40)). **40 remains
unanswered**, and opening 16 remains unresolved.

## The certificate

Q is short, so it is P exactly when each of its obligations leads to N. The
obligations are the even moves 2g for the gaps g of its half, and the half's
odd gaps above 1. [audit.py](audit.py) lists them twice, with the arena
referee's profile and with an independent coin-sum count
([audit.json](audit.json)), and accepts:
- 33 finite witnesses (all 16 odd obligations, and 17 even ones), replayed
  natively and in Python;
- 6 certified nodes: moves 4 and 6 reach C, 8 and 26 reach G, 14 reaches R,
  and 30 reaches O.

Each finite witness is a certificate `<prefix><move>-certificate.json`, in
the schema the campaign records use: prefix `q` for Q's obligations, and
`r40_` for the refutations, with parent {16,40}.
`python -m sylver.verify_finite_reply --python` replayed each from empty
memos with `native_solver.cpp` and the Python reference evaluator
([verification/](verification/)), and both report P with the same state
count.
- Q's replays total 4,525,687 states. The largest is its move 42 answered
  by 89, {16,20,42,46,89}, at 1,626,244.
- The refutations' total 39,264,642. The largest is 70's,
  {16,37,40,70}, at 38,439,250.

The audit then checks the thirteen refutations: each move is legal and
reaches a finite witness, a certified node, Q, or B28. For B28 it runs the
reply-38 record's own audit of B28.

**What it rests on.** The certified nodes used are C, E, G, O, P0, R and T.
Through G and O, Q's certificate rests on Sicherman's {8,10,22}, whose P
outcome comes from a periodicity computation, and on parameter 3 of Blok's
pairing family. The search looked for finite answers in their place. Q's
move 24 has one, 29, which replaces the node K. Q's moves 8, 26 and 30 have
no odd reply up to 201 that wins. B28's certificate rests on what the
reply-38 record lists. Like the other records, this one rests on the Quiet
End Theorem.

No mathematical priority claim is made.

## The search for an answer to 40

The search is recorded in [scan/](scan/). Its sweeps ran without
`--verify-memo`, so apart from what the audit checks, this section is
discovery output, not certified.

**Which answers it tried.**
- **a ≡ 2 (mod 4).** These give {16,40,a} gcd two and a short half, so the
  Quiet End Theorem lists the obligations, and the search can show the
  position P.
- **a ≡ 4 (mod 8).** These give gcd four, which the tools here do not cover.
- **Multiples of 8.** Only 8 and 24 are legal. They reach {8} and
  {16,24,40}, the gcd-eight positions 8·{1} and 8·{2,3}.
- **Odd answers.** These give finite positions.

**Odd answers.** The ledger's scan tried 3, the one odd gap above 1 of the
reduced pair {2,5}, and it fails. Here, one P-table sweep found that 5
through 33 all fail (3,167,594 P-positions, about a minute). A second found
that 35 through 57 fail too (156,248,856 P-positions); it stopped at its
one-hour limit during 59.

**Even answers a ≡ 2 (mod 4).** `screen.py` first looked for an obligation
reaching a known P-position, for every a up to 398. It then swept the odd
obligations of the survivors, stopping at the first P:

| a | Result |
| --- | --- |
| 6, 10, 14, 18, 22, 30, 34, 38 | an obligation reaches a known P-position (the table above) |
| 26, 42, 50, 62, 70 | an odd obligation reaches a finite P-position: 11, 23, 11, 61, 37 |
| 46, 54, 58 | every odd obligation leads to N |
| 66, 74, 78, 82, 86 | stopped with 3 to 16 odd obligations left: 86 at the cap of 100,000,000 P-positions, the others at the 30-minute limit |
| 90 to 398 | not swept |

62's finite witness, {16,40,61,62}, needs 286,533,125 states when solved
alone. A Python replay would need about 46 GB of this 62 GB host, so 62 is
refuted only by search.

For 46, 54 and 58, the even obligations decide:
- **46.** Its move 20 reaches {16,20,40,46} = Q, since 40 = 20+20. A pair
  search over the even replies of {16,40,46,60}, one of 46's children,
  found Q's 16 odd and 23 even obligations all leading to N. The audit now
  checks that proof.
- **54.** Five of its children are short. Its moves 52, 60, 68 and 76 reach
  positions whose odd obligations all lead to N, and 92's sweep stopped
  early. The first, **B54={16,40,52,54}** (half {8,20,26,27}, Frobenius
  number 65, 55 obligations), had all 33 of its even obligations answered
  too. So B54 is P by search, and 54 fails. B54 is not on Sicherman's list.
  - Its evidence is in `scan/evidence_16-40-52-54.json`: 46 finite
    witnesses, 1,650,024,795 states in all when each is solved alone, and
    nine routes to certified nodes.
  - Three of the witnesses are above 175 million states: its moves 98, 60
    and 78, answered by 175, 229 and 127, at 395,092,803, 365,742,433 and
    219,812,546. Certifying those would need native replays and sequential
    Kunz replays, as the reply-38 record did for B56's largest witnesses.
- **58.** The same way: its moves 36, 44, 60, 68 and 84 reach short
  positions whose odd obligations all lead to N. The first,
  **B58={16,36,40,58}** (half {8,18,20,29}, Frobenius number 59, 51
  obligations), had all 30 of its even obligations answered too. So B58 is P
  by search, and 58 fails. B58 is not on Sicherman's list either.
  - Its evidence is in `scan/evidence_16-36-40-58.json`: 44 finite
    witnesses, 517,445,319 states in all when each is solved alone, and
    seven routes to certified nodes. The largest witness is its move 118
    answered by 161, at 132,607,400 states. All are below the 175 million
    states up to which earlier records replayed in Python, so B58 can be
    certified the way Q is.

Each of 46, 54 and 58 thus fell to a short child that is P: the first one
tested, every time. The answers left below 90 are 66, 74, 78, 82 and 86.

No answer to 40 is known.
