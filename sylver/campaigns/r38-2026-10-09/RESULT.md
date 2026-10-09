# Reply 38 after the opening 16: three new P-positions refute four answers

After the opening 16, the lowest reply with no known answer is 38
([the ledger](../o16-2026-10-09/RESULT.md)). {16,38} has gcd two and a short
half, {8,19}. So by the Quiet End Theorem, a move answers 38 only if it is
one of {16,38}'s 98 obligations: 35 odd moves and 63 even ones.

This record certifies three new P-positions:

| Position | Half | Its Frobenius number | Obligations |
| --- | --- | ---: | ---: |
| I={16,20,22,24} | {8,10,11,12} | 25 | 21 |
| B28={16,28,38,40} | {8,14,19,20} | 45 | 38 |
| B24={16,24,38,44} | {8,12,19,22} | 45 | 38 |

They refute four candidate answers to 38:
- **24 and 44 do not answer 38.** {16,38,24} and {16,38,44} each move to B24,
  by 44 and by 24 respectively, so both are N.
- **28 and 40 do not answer 38.** {16,38,28} and {16,38,40} each move to
  B28, by 40 and by 28 respectively.

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

All three positions are short, so each is P exactly when each of its
obligations leads to N. The obligations are the even moves 2g for the gaps
g of the half, and the half's odd gaps above 1. [audit.py](audit.py) lists
them twice, with the arena referee's profile and with an independent
coin-sum count. It audits I first, then B28 and B24
([audit.json](audit.json)), and accepts:

| Evidence | I | B28 | B24 |
| --- | ---: | ---: | ---: |
| finite witness, native and Python replays | 17 | 30 | 31 |
| certified node | 4 | 8 | 6 |
| I is P (B24's move 20, answered by 22) | — | — | 1 |

Each finite witness is a certificate `<prefix><move>-certificate.json`, in
the schema the campaign records use. `python -m sylver.verify_finite_reply
--python` replayed it from empty memos with `native_solver.cpp` and with
the Python reference evaluator ([verification/](verification/)). Both report
P with the same state count. The replays total 58,116,949 states; the
largest, B24's move 90 answered by 241, has 15,386,349.

The audit then checks the ten refutations: each listed move is legal and
reaches B24, B28 or a certified node.

**What it rests on.** The certified nodes used are C, D, E, F, J and P0.
Through them the certificate rests on the Quiet End Theorem, the pairing
family {8,10,12,14} and {8,12,18,22}, as Y's does. It does not rest on
Sicherman's {8,10,22}: I's moves 8 and 10 and B28's move 50, which the
search first answered through {8,10,22} and the node M, have finite
witnesses instead.

No mathematical priority claim is made.

## The search for an answer to 38

The search is recorded in [scan/](scan/). Its sweeps ran without
`--verify-memo`. So apart from the ten refutations the audit checks
(through B24, B28 and the nodes C, E, F and P0), this section is discovery
output, not certified.

| Obligations of {16,38} | Count | N so far | Open |
| --- | ---: | ---: | ---: |
| odd | 35 | 28 | 7 |
| even, short child | 17 | 12 | 5 |
| even, long child | 46 | 8 | 38 |

- **Odd.** The ledger's scan showed the 24 smallest odd candidates are N.
  One more shared-memo sweep here showed that 71, 69, 77 and 79 are N, then
  stopped during 85 at its 1,400,000,000-state cap. 85, 87, 93, 101, 109,
  117 and 125 are open.
- **Short even.**
  - For a = 6, 12, 20, 60 and 136, an odd move wins from {16,38,a}
    ([scan/odd_filter.jsonl](scan/odd_filter.jsonl)).
  - Certified nodes refute 4, 6, 8, 12 and 22, as above; the audit checks
    these.
  - B24 and B28 refute 24, 28, 40 and 44, above.
  - 56, 72 and 88 are odd-complete: every odd obligation is N.
    - For 56, 31 of 39 even obligations have a winning reply. The short
      child {16,38,56,60} has no P child among its short children, so it is
      probably P, which would refute 56. Seven long children are open.
    - 72 and 88 were still being resolved.
  - 104 and 120 have odd obligations that the sweeps could not finish.
- **Long even.** A long candidate is N as soon as one winning reply is
  found.
  - Sweeps found a winning odd reply for 2 (3), 10 (9), 18 (5), 26 (97),
    30 (271), 34 (53) and 36 (123).
  - 14 moves to E by 8.
  - For 42, the 106 odd replies classified are all N. Four more (205, 213,
    215 and 221) were not classified: their batches stopped at the state cap
    or the 1,800-second timeout.
  - The rest have not been searched.

## Reproduction

```sh
python sylver/campaigns/r38-2026-10-09/audit.py > /tmp/r38-audit.json
python -m sylver.verify_finite_reply --certificate sylver/campaigns/r38-2026-10-09/b24_90-certificate.json \
    --output /tmp/b24_90 --python
```
