# U={16,26,88} is P if and only if X={16,26,82,88} is N

U is the position after 16, 26 and 88 have been named. If U is P, then 88
answers 26 and the reply 26 to the opening 16 loses. The September 5
verification report reduced U P to X N and Q N (Q={16,26,88,98}), resting
on the project's July audit of U's other branches
([RUN_MOVE_26_U_SUBTREE.txt](../../RUN_MOVE_26_U_SUBTREE.txt)), which it did
not repackage. This record checks that premise obligation by obligation.

U has gcd two, and its half {8,13,44} is a quiet ender, so U is short: by
the Quiet End Theorem, U is P exactly when each of its **59 obligations**
(the 38 even moves 2g for the gaps g of the half, and the half's 21 odd
gaps above 1) leads to an N-position. [audit.py](audit.py) lists them twice,
with the arena referee's profile and an independent coin-sum count, and
accepts only these kinds of evidence ([audit.json](audit.json)):

| Evidence | Obligations | Moves |
| --- | ---: | --- |
| Book certificate | 52 | 2, 3, 4, 5, 6, 7, 9, 10, 11, 14, 15, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 30, 31, 33, 34, 35, 38, 40, 41, 43, 44, 46, 49, 50, 51, 54, 59, 60, 62, 66, 67, 72, 75, 76, 86, 92, 102, 108, 118, 124, 134, 150 |
| finite witness, native and Python replays | 1 | 70 |
| winning reply to a certified infinite P-position | 4 | 8, 12, 36, 56 |
| reply 62 into W, which is P | 1 | 98 |
| open: X={16,26,82,88} | 1 | 82 |
| **total** | **59** | |

- **Book certificate:** a certificate in The Book for the obligation's
  position, re-hashed and checked for its root, outcome N and verifier
  profile, and citing no baseline fact. The fixed verifier replayed it with
  a fresh memo when it was admitted (twice for 37 of them, once for the 15
  admitted after the Book's verification profile was raised to 32 GB), and
  `python -m sylver.arena book verify` replays it again.
- **Finite witness:** move 70 is answered by 261, and its destination
  {16,26,70,88,261} (Frobenius number 385) needs about 200 million states;
  its admission to The Book was tried and exceeded the 32 GB verification
  profile at 16 words, so like W's
  large witnesses it has a native and a Python replay
  ([u70-certificate.json](u70-certificate.json),
  [verification/u70/](verification/u70/)): P, 201,555,961 states in
  both, 1,679 s native and 12,173 s Python.
- **Certified node:** the listed reply reaches a P-position certified in
  `sylver/short_certificates.py`: G={8,20,26} for move 8, F={12,14,16} for
  12, and V={16,26,36,56} for 36 and 56.
- **W is P:** move 98 reaches Q, and Q + 62 = W={16,26,62,98}, which is P
  ([w-p-2026-09-27](../w-p-2026-09-27/RESULT.md)); the audit re-runs W's own
  audit and requires outcome P.

The Book's replay counts agree exactly with both Python reproductions the
July record kept: 57,309,624 states for {16,26,88,92,93}
and 62,403,662 for {16,26,88,91,124}. Move 24 no longer needs K: its
position {16,24,26} is answered by 15, reaching {15,16,24,26}, the finite
P-position that also answers W's move 24 in The Book (its sweep,
`ledger-u24.jsonl`, found no other odd witness from 121 to 601).
Odd-witness sweeps found no finite replacement for the other
certified-node routes: every odd reply is N up to 601 for {16,26,36} (U's
and W's move 36) and {8,26} (move 8), up to 393 for {16,26,56} (move 56),
and, by W's record, up to 977 for {12,16,26} (move 12), counting replies
the cache already classified ([scan/](scan/), `ledger-u*.jsonl`; a few rows
of out-of-memory batches lack the memo check and are not counted).

Every obligation except move 82 is covered, so **U is P if and only if X
is N**, and U N if and only if X is P. The claim rests on the Quiet End
Theorem, the finite solvers and The Book's replays, and, through the
certified nodes G, F, V and through W, on the three published
P-positions the repository explicitly assumes: {8,10,12,14} and
{8,12,26,30} from Blok's pairing family, and Sicherman's {8,10,22}.

## X, the last obligation

X's 32 even replies were all refuted in Attempt 20, so X is N exactly when
some odd reply r makes X+r a P-position. X is long (its half {8,13,41,44}
is not a quiet ender), so the Quiet End Theorem gives no finite cover of
X. The audit reports X's classified odd replies: 203 from the exact cache
(every odd reply up to 407) and 140 memo-verified sweep rows, all N; no
odd reply is P, and the first unclassified one is **689**.

The new rows come from shared-memo sweeps of `sylver/parallel_solver.cpp`
on ten threads with `--verify-memo` ([scan/ledger-x.jsonl](scan/ledger-x.jsonl)):
one memo for a batch of replies, so after the first reply of a batch the
others cost seconds.

| Batch | First reply: states, seconds | Batch states | Wall (s), with the memo check |
| --- | --- | ---: | ---: |
| 409–439 (16 replies) | 409: 378,922,539, 412 | 416,189,016 | 564 |
| 441–457 (9) | 441: 409,246,109, 551 | 441,892,278 | 682 |
| 459–521 (32) | 459: 428,805,590, 719 | 495,810,547 | 930 |
| 523–601 (40) | 523: 487,543,968, 779 | 562,134,312 | 1,009 |
| 603–649 (24) | 603: 546,512,584, 851 | 599,363,424 | 1,041 |
| 651–665 (8) | 651: 578,719,126, 952 | 614,517,665 | 1,129 |
| 667–681 (8) | 667: 603,766,693, 996 | 628,686,315 | 1,169 |
| 683–687 (3) | 683: 620,080,435, 1,040 | 630,722,566 | 1,180 |

The first two batches ran on the engine of PR #26; beyond reply 457 the
batches needed PR #30's leaner memo (fingerprinted shards filled to 7/8
that grow by half), since a doubling table would have needed about 45 GB.
The last batches ended at 628.7 and 630.7 million states, just below the
636 million that 13-word keys fit in about 48 GB, and reply 683 alone
needed 620 million; the next growth step would need about 72 GB, more
than this 62 GB host, so further replies need a leaner memo or a larger
machine.
Every row is N and each is an engine result whose memo passed its
certificate check, not an independent replay; only a P row would need one,
and there is none.

No mathematical priority claim is made.

## Reproduction

```sh
python sylver/campaigns/u-2026-09-27/audit.py > /tmp/u-audit.json
python -m sylver.arena book verify
```
