# Reply 38 after the opening 16: four P-positions refute five answers

After the opening 16, the lowest reply with no known answer is 38
([the ledger](../o16-2026-10-09/RESULT.md)). {16,38} has gcd two and a short
half, {8,19}. So by the Quiet End Theorem, a move answers 38 only if it is
one of {16,38}'s 98 obligations: 35 odd moves and 63 even ones.

This record certifies four P-positions:

| Position | Half | Its Frobenius number | Obligations |
| --- | --- | ---: | ---: |
| I={16,20,22,24} | {8,10,11,12} | 25 | 21 |
| B28={16,28,38,40} | {8,14,19,20} | 45 | 38 |
| B24={16,24,38,44} | {8,12,19,22} | 45 | 38 |
| B56={16,38,56,60} | {8,19,28,30} | 69 | 56 |

**Correction (October 10).** This record first called all four new. I and B24
are on George Sicherman's [list of P-positions](https://sicherman.net/sylver/ppos.html)
(last updated September 28), so for them it is an independent confirmation.
B28 and B56 are not on that list.

They refute five candidate answers to 38:
- **24 and 44 do not answer 38.** {16,38,24} and {16,38,44} each move to B24,
  by 44 and by 24 respectively, so both are N.
- **28 and 40 do not answer 38.** {16,38,28} and {16,38,40} each move to
  B28, by 40 and by 28 respectively.
- **56 does not answer 38.** {16,38,56} moves to B56 by 60.

The audit also checks six refutations through certified nodes:
- 4 and 6 (6 and 4 reach C={4,6});
- 8 and 14 (14 and 8 reach E={8,14});
- 12 (14 reaches F={12,14,16});
- 22 (12 reaches P0={12,16,22}).

**One question from the Y record is settled.** The Y record left open
whether 38 answers the reply 28, that is, whether {16,28,38} is P. It is N:
its move 40 reaches B28.

No answer to 38 is known, so **38 remains the lowest unanswered reply**.
Opening 16 remains unresolved.

## The certificate

All four positions are short, so each is P exactly when each of its
obligations leads to N. The obligations are the even moves 2g for the gaps
g of the half, and the half's odd gaps above 1. [audit.py](audit.py) lists
them twice, with the arena referee's profile and with an independent
coin-sum count. It audits I first, then B28, B24 and B56
([audit.json](audit.json)), and accepts:

| Evidence | I | B28 | B24 | B56 |
| --- | ---: | ---: | ---: | ---: |
| finite witness, native and Python replays | 17 | 30 | 31 | 42 |
| finite witness, native and Kunz replays | — | — | — | 4 |
| certified node | 4 | 8 | 6 | 6 |
| an earlier position of this audit is P | — | — | 1 (I) | 4 (B24, B28) |

Each finite witness is a certificate `<prefix><move>-certificate.json`, in
the schema the campaign records use.
- `python -m sylver.verify_finite_reply --python` replayed it from empty
  memos with `native_solver.cpp` and with the Python reference evaluator
  ([verification/](verification/)). Both report P with the same state
  count.
- B56's four witnesses above 175 million states were replayed
  differently. They are its moves 122, 84, 90 and 74, at 179,722,136 to
  423,748,850 states.
  - Each has a `native_solver.cpp` replay and a sequential
    `kunz_solver.cpp` replay (`--threads 1 --verify-memo`) with equal state
    counts.
  - The Kunz source is kept in
    [verification/sources/](verification/sources/), and the audit pins its
    hash and checks the command each transcript records.
  - The Python evaluator needs about 125 to 180 bytes per state. These four
    would need 22 to 76 GB of this 62 GB host, which other work shares.
    Earlier records drew the same line: Z replayed a 145-million-state
    witness in Python, and its 262- and 297-million-state ones by Kunz.
  - B56's three witnesses from 106 to 138 million states (moves 100, 106
    and 42) have Python replays.
- The replays total 1,810,987,248 states:
  - 656,850,201 replayed natively and in Python;
  - 1,154,137,047 replayed natively and by Kunz.
- The largest witness is B56's move 74 answered by 205,
  {16,38,56,60,74,205}, at 423,748,850 states.

The audit then checks the eleven refutations: each listed move is legal and
reaches B24, B28, B56 or a certified node.

**What it rests on.** The certified nodes used are C, D, E, F, J and P0.
Through them the certificate rests on the Quiet End Theorem, the pairing
family {8,10,12,14} and {8,12,18,22}, as Y's does. It does not rest on
Sicherman's {8,10,22}: I's moves 8 and 10 and B28's move 50, which the
search first answered through {8,10,22} and the node M, have finite
witnesses instead.

No mathematical priority claim is made.

## The search for an answer to 38

The search is recorded in [scan/](scan/). Its sweeps ran without
`--verify-memo`. So apart from the eleven refutations the audit checks
(through B24, B28, B56 and the nodes C, E, F and P0), this section is
discovery output, not certified.

| Obligations of {16,38} | Count | N so far | Open |
| --- | ---: | ---: | ---: |
| odd | 35 | 28 | 7 |
| even, short child | 17 | 13 | 4 |
| even, long child | 46 | 14 | 32 |

- **Odd.** The ledger's scan showed the 24 smallest odd candidates are N.
  One more shared-memo sweep here showed that 71, 69, 77 and 79 are N, then
  stopped during 85 at its 1,400,000,000-state cap. 85, 87, 93, 101, 109,
  117 and 125 are open.
- **Short even.**
  - For a = 6, 12, 20, 60 and 136, an odd move wins from {16,38,a}
    ([scan/odd_filter.jsonl](scan/odd_filter.jsonl)).
  - Certified nodes refute 4, 6, 8, 12 and 22, as above; the audit checks
    these.
  - B24, B28 and B56 refute 24, 28, 40, 44 and 56, above.
  - The other short candidates form a ladder with 56 and 136: a = 56 + 16k,
    for 72, 88, 104 and 120.
    - Since 16 is in every position here, a candidate's obligation b, for a
      lower rung b, leads back to {16,38,b}. So at most one rung is P: a P
      rung refutes every rung above it.
    - 136 falls to an odd obligation (37) and 56 to B56. An answer among the
      short candidates must be the first P rung among 72, 88, 104 and 120.
  - 72 and 88 are odd-complete: every odd obligation is N.
    - 72's obligation 56 is answered through B56. The deep replies 129 and
      69 answer its obligations 58 and 66.
    - 72's long children 68, 78 and 84 have no even reply into a short
      P-position and no odd winner found so far. The hardest of their odd
      replies each need about 300 to 600 million states: those from 81 on for 78,
      from 87 on for 84, and from about 150 on for 68.
    - Every short child of 72 is N, so a refutation of 72 would need a long
      P-position, which the Quiet End Theorem cannot certify.
    - 88's obligation 72 leads back to {16,38,72}.
  - 104 and 120 have odd obligations that the sweeps could not finish.
- **Long even.** A long candidate is N as soon as one winning reply is
  found.
  - Sweeps found a winning odd reply for 2 (3), 10 (9), 18 (5), 26 (97),
    30 (271), 34 (53), 36 (123), 50 (79), 58 (11), 78 (27), 94 (43),
    98 (31) and 100 (41).
  - 14 moves to E by 8.
  - 18 stayed open within the sweeps' state caps: 42, 46, 52, 62, 66, 68,
    74, 82, 84, 90, 106, 110, 116, 122, 126, 132, 138 and 142. For 42, the
    106 odd replies classified are all N, and four more (205, 213, 215 and
    221) were not classified: their batches stopped at the state cap or the
    1,800-second timeout.
  - The other 14, from 148 up, have not been searched.

## Reproduction

```sh
python sylver/campaigns/r38-2026-10-09/audit.py > /tmp/r38-audit.json
python -m sylver.verify_finite_reply --certificate sylver/campaigns/r38-2026-10-09/b24_90-certificate.json \
    --output /tmp/b24_90 --python
```
