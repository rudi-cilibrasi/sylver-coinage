# Answers to the replies after the opening 16, up to 200

After the opening 16, each reply r loses if some answer a makes {16,r,a} a
P-position. Odd replies lose by Hutchings' theorem. This ledger collects
the even replies up to 200 that now have an answer, with the evidence for
each. [audit.py](audit.py) checks every row ([audit.json](audit.json)).

**Every even reply up to 36 now has an answer** (32 is not a legal reply,
since it is a multiple of 16). The lowest unanswered reply is **38**.
Opening 16 remains unresolved.

| Reply | Answer | Position reached | Evidence |
| ---: | ---: | --- | --- |
| 2–24 | (table) | | the certified table `OPENING_16_EVEN_RESPONSES` (11 rows) |
| 26 | 88 | U={16,26,88} | [U campaign](../u-2026-09-27/RESULT.md) |
| 28 | 58 | Y={16,28,58} | [Y campaign](../y-2026-10-07/RESULT.md) |
| 30 | 56 | Z={16,30,56} | [Z campaign](../z-2026-10-08/RESULT.md) |
| 34 | 20 | T={16,20,34} | certified node T (the table's answer to 20, used the other way) |
| 36 | 23 | {16,23,36} | finite witness, native and Python replays: 1,179,780 states |
| 56 | 30 | Z | Z campaign |
| 58 | 11 | {11,16,58} | finite witness, native and Python replays: 14,775 states |
| 62 | 37 | {16,37,62} | finite witness, native and sequential Kunz replays: 314,785,111 states |
| 86 | 33 | {16,33,86} | finite witness, native and sequential Kunz replays: 382,469,318 states |
| 88 | 26 | U | U campaign |
| 90 | 17 | {16,17,90} | finite witness, native and Python replays: 1,280,911 states |
| 140 | 13 | {13,16,140} | finite witness, native and Python replays: 129,414 states |
| 156 | 21 | {16,21,156} | finite witness, native and Python replays: 10,740,605 states |

## The finite answers

The finite answers come from one scan ([scan/](scan/)).
- **The method.** For each even reply r from 36 to 200, with d = gcd(16, r),
  it swept the odd gaps m > 1 of the reduced pair {16/d, r/d}. Each sweep
  shared one `kunz_solver.cpp` memo and stopped at the first P.
- **The answers.** It found eight finite answers: those above, and
  150 → 31.
  - {16,31,150} needs 571,026,631 states, and it was not replayed. At the
    142 bytes per state that `native_solver.cpp` used for X, a replay would
    need about 75 GiB, more than this host's 62 GiB. So it is not in the
    ledger.
- **Gaps in the scan.** Most other sweeps stopped at the scan's
  800,000,000-state memo cap before classifying every candidate. Even a
  complete sweep tries only the odd gaps of the reduced pair. So finding no
  answer for a reply here does not show that it has none.
  - The sweep for 38 classified 24 of its 35 odd candidates.
  - The sweep for 198 failed. Its candidate 685 needs a Kunz coordinate above
    the engine's limit of 127, and the sweep's candidates share one memo.

Each finite answer has a certificate `o<r>-certificate.json`, in the schema
the campaign records use, with parent [16].
`python -m sylver.verify_finite_reply --python` replayed it from empty memos
with `native_solver.cpp` and the Python reference evaluator
([verification/](verification/)), and both report P with the same state
count. Two destinations, for 62 and 86, are too large for the Python
evaluator here. Their second replay is a sequential `kunz_solver.cpp` run
with `--verify-memo`, and its source is pinned by hash.

**What it rests on.** The ledger's finite answers, and the certified table's
finite rows (2 → 3, 6 → 7, 10 → 9, 18 → 5), assume nothing beyond the finite
solvers. The table's node rows, the node T, and the U, Y and Z campaigns rest
on the Quiet End Theorem and on published P-positions the repository
assumes; their records say which.

No mathematical priority claim is made.

## Reproduction

```sh
python sylver/campaigns/o16-2026-10-09/audit.py > /tmp/o16-audit.json
python -m sylver.verify_finite_reply --certificate sylver/campaigns/o16-2026-10-09/o36-certificate.json \
    --output /tmp/o36 --python
```
