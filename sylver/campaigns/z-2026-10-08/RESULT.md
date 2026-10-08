# Z={16,30,56} is P: 56 answers the reply 30 to the opening 16

Z is the position after the opening 16, the reply 30 and the answer 56.
**Z is P**, so after the opening 16 the reply 30 loses: 56 answers it.

The opening-16 replies now answered:
- **Even replies 2–24:** the repository's certified table answers each one.
- **26:** answered by 88, through U ([U record](../u-2026-09-27/RESULT.md)).
- **28:** answered by 58, through Y ([Y record](../y-2026-10-07/RESULT.md)).
- **30:** answered by 56, here.
- **Odd replies:** lose by Hutchings' theorem.

32 is not a legal reply, since it is a multiple of 16. 34 is answered
by 20, since the certified node T={16,20,34} works both ways. The lowest
unanswered reply is now 36. Opening 16 remains unresolved.

## The certificate

The proof has two levels. Z's move 44 reaches Z+44 = {16,30,44,56}. That
position is answered by 40, which reaches a second new P-position,
**Z′={16,30,40,44}**. [audit.py](audit.py) audits Z′ first and then Z
([audit.json](audit.json)).

Both positions have gcd two and quiet-ender halves:

| Position | Half | Its Frobenius number | Obligations |
| --- | --- | ---: | ---: |
| Z′={16,30,40,44} | {8,15,20,22} | 49 | 40 |
| Z={16,30,56} | {8,15,28} | 65 | 52 |

So both are short. By the Quiet End Theorem, each is P exactly when each of
its obligations leads to N. The obligations are the even moves 2g for the
gaps g of the half, and the half's odd gaps above 1. The audit lists them
twice, with the arena referee's profile and with an independent coin-sum
count. It accepts:

| Evidence | Z′ | Z |
| --- | ---: | ---: |
| finite witness, native and Python replays | 35 | 42 |
| finite witness, native and Kunz replays (70→311, 130→225) | — | 2 |
| winning reply to a certified node | 5 (C, E, F) | 7 (C, E, F, O, K) |
| the reply 40 into Z′, which is P | — | 1 (move 44) |
| **total** | **40** | **52** |

- **Finite witnesses.** A certificate `zp<m>-` or `z<m>-certificate.json`
  names the reply w to the obligation m. The destination has gcd one.
  `python -m sylver.verify_finite_reply --python` replayed it from empty
  memos with `native_solver.cpp` and with the Python reference evaluator,
  and both report P with the same state count ([verification/](verification/)).
  The audit re-hashes and parses every transcript.
  - Z′'s 35 replays take 83,555,568 states.
  - Z's native and Python replays take 813,193,935.
- **Native and Kunz witnesses.** Two of Z's destinations are too large for
  the Python evaluator here. Their second replay is a sequential
  `kunz_solver.cpp` run instead: one thread, so it reports
  `native_solver.cpp`'s count, and `--verify-memo` with its scalar
  reference moves. Every odd reply up to 601 to Z+70 and Z+130 was swept,
  and these are the only P answers. That sweep is unverified discovery
  output, which the certificate does not need:
  - Z+70+311 = {16,30,56,70,311}: 297,106,878 states;
  - Z+130+225 = {16,30,56,130,225}: 262,076,190 states.
- **Kunz counts.** The Kunz engine's sequential counts equal the native
  counts for every witness of both positions.

**What it rests on.** The Quiet End Theorem, which reduces each position to
its obligations. Z′ uses only the nodes C, E and F, and through E and F,
Blok's pairing family ({8,10,12,14}). Z also uses O (move 20 → 8) and K
(move 24 → 10). The positions Z+20 = {16,20,30} and Z+24 = {16,24,30} are
short, and an unverified sweep found all their odd obligations N, so they
have no finite odd answer. O and K rest on Sicherman's {8,10,22}, so Z does too, as U and W
do; Y does not.

## How Z was found

The scripts and outputs are in [scan/](scan/).

1. **Odd replies.** {16,30} is short, with half {8,15}, which has Frobenius
   number 97. All 27 of its odd obligations are N, so 30 has no odd answer.
   This comes from one sweep with `--verify-memo`, whose memo of
   271,657,062 entries passed its check ([scan/odd_30.txt](scan/odd_30.txt)).
2. **Short even candidates.** 17 of 30's 49 even obligations e give a
   short {16,30,e}. Filtering on their odd obligations left 9 candidates:
   4, 12, 14, 20, 24, 44, 50, 56 and 104.
3. **Even obligations.**
   - **Refuted by certified nodes:** 4 (by C), 12 (F), 14 (E), 20 (O) and
     24 (K).
   - **56** had one obligation left: 44, whose child Z+44 = {16,30,44,56}
     is short and needed an even reply.
   - **44** had the mirror child, 56, the same position, among its open
     obligations.
   - **Z+44** resolves except for its move 40, which reaches Z′.
   - **Z′ resolves completely**, so Z′ is P. Then 40 wins from Z+44, which
     makes Z+44 N, and Z P. The same move 40 refutes 44 as an answer.
   - **50** keeps two long children with no odd witness up to 401, and was
     not pursued.
   - **104's** sweeps stopped early. It is refuted outright anyway: 104 lies
     in {16,56}, so {16,30,104} + 56 = Z, which is P.
   - These search sweeps ran without `--verify-memo`. Only the {16,30} odd
     sweep below and the certificate's own replays are verified.

No mathematical priority claim is made.

## Reproduction

```sh
python sylver/campaigns/z-2026-10-08/audit.py > /tmp/z-audit.json
python -m sylver.verify_finite_reply --certificate sylver/campaigns/z-2026-10-08/zp66-certificate.json \
    --output /tmp/zp66 --python
```
