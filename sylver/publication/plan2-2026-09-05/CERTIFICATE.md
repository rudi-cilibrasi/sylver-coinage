# Certificate inventory

Root: **{16,26,54,60,62} P**. All 38 required children are N.

This table is generated from `evidence/certificate.json`.

| Opponent move | Refutation | P destination |
| ---: | --- | --- |
| 2 | Reply 3 | {2,3} |
| 3 | Native winning reply 2 | Exact finite N evaluation |
| 4 | Reply 6 | {4,6} |
| 5 | Native winning reply 18 | Exact finite N evaluation |
| 6 | Reply 4 | {4,6} |
| 7 | Native winning reply 6 | Exact finite N evaluation |
| 8 | Reply 20 | {8,20,26} |
| 9 | Native winning reply 10 | Exact finite N evaluation |
| 10 | Reply 24 | {10,16,24} |
| 11 | Native winning reply 40 | Exact finite N evaluation |
| 12 | Reply 14 | {12,14,16} |
| 14 | Reply 12 | {12,14,16} |
| 15 | Native winning reply 22 | Exact finite N evaluation |
| 17 | Native winning reply 23 | Exact finite N evaluation |
| 18 | Reply 5 | {5,16,18} |
| 19 | Native winning reply 44 | Exact finite N evaluation |
| 20 | Reply 8 | {8,20,26} |
| 22 | Reply 15 | {15,16,22,26} |
| 23 | Native winning reply 14 | Exact finite N evaluation |
| 24 | Reply 10 | {10,16,24} |
| 25 | Native winning reply 28 | Exact finite N evaluation |
| 28 | Reply 25 | {16,25,26,28,62} |
| 30 | Reply 47 | {16,26,30,47,54} |
| 33 | Native winning reply 79 | Exact finite N evaluation |
| 34 | Reply 167 | {16,26,34,54,62,167} |
| 36 | Reply 23 | {16,23,26,36,54,60} |
| 38 | Reply 77 | {16,26,38,60,62,77} |
| 40 | Reply 11 | {11,16,26,40} |
| 41 | Native winning reply 39 | Exact finite N evaluation |
| 44 | Reply 19 | {16,19,26,44,62} |
| 46 | Reply 25 | {16,25,26,46,54,60} |
| 49 | Native winning reply 46 | Exact finite N evaluation |
| 50 | Reply 57 | {16,26,50,54,57,60,62} |
| 56 | Reply 91 | {16,26,54,56,60,62,91} |
| 66 | Reply 31 | {16,26,31,54,60,66} |
| 72 | Reply 13 | {13,16,54,60,62,72} |
| 82 | Reply 71 | {16,26,54,60,62,71,82} |
| 98 | Reply 27 | {16,26,27,60,62,98} |

The 13 exceptional odd moves are 3,5,7,9,11,15,17,19,23,25,33,41,49.
The half-position is quiet with Frobenius number 49. The Quiet End
Theorem covers all other odd moves; no finite scan substitutes for this tail proof.

## Dependency inventory

| Evidence kind | Facts |
| --- | ---: |
| finite-exact | 62 |
| public-theorem | 3 |
| short-cover | 5 |
| winning-reply | 49 |

Published P leaves, explicitly assumed from established results:

- {8,10,12,14}: [published P list](https://sicherman.net/sylver/ppos.html).
- {8,10,22}: [published P list](https://sicherman.net/sylver/ppos.html).
- {8,12,26,30}: [published P list](https://sicherman.net/sylver/ppos.html).

The {8,10,22} odd tail is additionally recomputed by the included
periodicity control. The family leaves {8,10,12,14} and {8,12,26,30}
use the established infinite pairing result. The verifier does not
replace that result with checks of a finite prefix.

## Release verification

All 62 finite leaves were recomputed with a separately compiled native executable.
Of these, 41 small leaves also matched the Python reference evaluator.
All graph identities and coverage checks passed. The test suite has 27 tests.

`scan-*.txt` logs use **cumulative** native state counts within each shared-memo scan.
Certificate leaf state counts come from separate single-position evaluations.
