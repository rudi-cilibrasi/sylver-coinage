# A completed short P-position certificate

The position **B={16,26,56,62,66} is P**: the next player loses with optimal
play. The final response found is **76 → 247**. The resulting finite position
{16,26,56,62,66,76,247} is P, with Frobenius number 333.

B/2={8,13,28,31,33} is a quiet ender with Frobenius number 51. The Quiet End
Theorem handles every odd move outside its exceptional odd gaps. The 14
exceptional odd moves are:

`3,5,7,9,11,15,17,19,23,25,27,35,43,51`

Each exceptional odd child is N by exact finite computation. The remaining
26 legal even moves have the following responses; adjoining each move and
its response to B gives a P-position, after removing redundant generators.

| Opponent move | Winning response |
| --- | --- |
| 2 | 3 |
| 4 | 6 |
| 6 | 7 |
| 8 | 20 |
| 10 | 24 |
| 12 | 14 |
| 14 | 12 |
| 18 | 5 |
| 20 | 8 |
| 22 | 15 |
| 24 | 10 |
| 28 | 25 |
| 30 | 119 |
| 34 | 19 |
| 36 | 53 |
| 38 | 51 |
| 40 | 11 |
| 44 | 21 |
| 46 | 50 |
| 50 | 46 |
| 54 | 91 |
| 60 | 33 |
| 70 | 89 |
| 76 | 247 |
| 86 | 143 |
| 102 | 67 |

The two responses 46→50 and 50→46 use T={16,26,46,50,56} P. Its certificate
in turn uses S={16,26,30,34} P. Both subsidiary complete covers are included
in the compact certificate.

## Verification and dependencies

* [b-certificate.json](b-certificate.json): all 144 proof nodes, with complete
  move covers and exact one-move semigroup identities.
* [b-verification/receipt.json](b-verification/receipt.json): all **69 finite
  leaves** recomputed with an initially empty shared memo; **63,503,395 states**
  in **267.20 seconds**. No inherited outcome cache was loaded.
* [b76-247-standalone.json](b76-247-standalone.json): the decisive P-position
  separately recomputed with a fresh memo, 60,797,798 states, 257.49 seconds.
* [pair-verification.json](pair-verification.json): a separate Python replay
  of all 45 finite leaves of the two subsidiary certificates.

The infinite dependencies remain explicit: the Quiet End Theorem and the
repository P certificates {4,6}, {8,12,26,30}, {8,20,26}, {10,16,24},
{12,14,16}, and {14,16,20,26}. This result does not claim to independently
reprove those established infinite certificates.

Reproduce the complete finite replay and structural audit from the repo root:

```sh
python sylver/campaigns/targeted-2026-09-22/verify_b.py --output /tmp/b-check
```

## Consequence for W

After move 66 from W={16,26,62,98}, 98 is redundant because 98=66+2·16.
Replying 56 therefore reaches B. This refutes W's move 66.

[W's updated frontier](w-frontier.json) has **45 of 52 obligations covered**,
with seven even moves unresolved: **70,86,92,102,108,118,134**. W, Q, X,
and opening 16 remain unresolved. No novelty or complete-game solution is
claimed here.
