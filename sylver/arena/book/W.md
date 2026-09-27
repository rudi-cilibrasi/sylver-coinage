# The Book of W

W = {16,26,62,98} is a node of the move-26 program. W is short, and its obligations are the 52 moves
the Quiet End Theorem leaves: the 34 even moves 2g for the gaps g of its half {8,13,31,49}, and the
half's 18 odd gaps above 1; all 52 are covered, so **W is P** ([campaign record](../../campaigns/w-p-2026-09-27/RESULT.md), which lists what it rests on: the Quiet End Theorem and, through moves 12 and 36, three published P-positions). Hence Q={16,26,88,98} is N (Q + 62 = W), and U={16,26,88} P now needs only X={16,26,82,88} N. This table records which coverings are
self-contained certificates in The Book, replayed by the fixed verifier with a fresh memo and
no inherited cache.

**45 of 52 covered obligations** are certified here by self-contained certificates; 5 more have finite witnesses not yet in the Book; 2 depend on infinite P positions outside the proof language (named in each row); none is open.

| Move | Position | Status | Proof of record | C | States | V (s) |
| ---: | --- | --- | --- | ---: | ---: | ---: |
| 2 | `{2}` | **Book** | reply 3 → `{2,3}` | 128 | 1 | 0.179 |
| 3 | `{3,16,26}` | **Book** | finite leaf | 81 | 2 | 0.171 |
| 4 | `{4,26}` | **Book** | reply 6 → `{4,6}` (Quiet End cover) | 286 | 1 | 0.150 |
| 5 | `{5,16}` | **Book** | finite leaf | 75 | 62 | 0.171 |
| 6 | `{6,16,26}` | **Book** | reply 7 → `{6,7,16}` | 146 | 21 | 0.150 |
| 7 | `{7,16,26}` | **Book** | finite leaf | 81 | 31 | 0.175 |
| 8 | `{8,26,62}` | **Book** | reply 49 → `{8,26,49,62}` | 155 | 18,604 | 0.287 |
| 9 | `{9,16,26}` | **Book** | finite leaf | 81 | 340 | 0.174 |
| 10 | `{10,16}` | **Book** | reply 9 → `{9,10,16}` | 144 | 213 | 0.150 |
| 11 | `{11,16,26,62}` | **Book** | finite leaf | 89 | 4,089 | 0.196 |
| 12 | `{12,16,26}` | depends on {12,14,16} | reply 14 | | | |
| 14 | `{14,16,26}` | **Book** | reply 23 → `{14,16,23,26}` | 159 | 5,559 | 0.190 |
| 15 | `{15,16,26}` | **Book** | finite leaf | 83 | 10,911 | 0.233 |
| 17 | `{16,17,26,62}` | **Book** | finite leaf | 89 | 49,212 | 0.461 |
| 18 | `{16,18,26}` | **Book** | reply 5 → `{5,16,18}` | 150 | 50 | 0.177 |
| 19 | `{16,19,26,62,98}` | **Book** | finite leaf | 95 | 67,254 | 0.623 |
| 20 | `{16,20,26}` | **Book** | reply 14 → `{14,16,20,26}` (Quiet End cover) | 2181 | 11,114 | 0.225 |
| 22 | `{16,22,26,62}` | **Book** | reply 15 → `{15,16,22,26}` | 165 | 5,956 | 0.209 |
| 23 | `{16,23,26}` | **Book** | finite leaf | 83 | 10,306 | 0.248 |
| 24 | `{16,24,26,62}` | **Book** | reply 15 → `{15,16,24,26}` | 165 | 7,377 | 0.181 |
| 25 | `{16,25,26,62}` | **Book** | finite leaf | 89 | 186,709 | 1.521 |
| 27 | `{16,26,27,62,98}` | **Book** | finite leaf | 95 | 61,349 | 0.565 |
| 28 | `{16,26,28,62}` | **Book** | reply 25 → `{16,25,26,28,62}` | 171 | 105,133 | 0.894 |
| 30 | `{16,26,30}` | **Book** | reply 73 → `{16,26,30,73}` | 159 | 2,378,741 | 28.299 |
| 33 | `{16,26,33,62}` | **Book** | finite leaf | 89 | 1,533,942 | 18.556 |
| 34 | `{16,26,34,62}` | **Book** | reply 39 → `{16,26,34,39,62}` | 171 | 800,890 | 5.902 |
| 35 | `{16,26,35,62,98}` | **Book** | reply 24 → `{16,24,26,35,62}` | 177 | 209,885 | 1.278 |
| 36 | `{16,26,36}` | depends on V={16,26,36,56} | reply 56 | | | |
| 38 | `{16,26,38,62,98}` | **Book** | reply 55 → `{16,26,38,55,62,98}` | 183 | 3,240,895 | 27.461 |
| 40 | `{16,26,40,62}` | **Book** | reply 11 → `{11,16,26,40}` | 165 | 3,740 | 0.157 |
| 41 | `{16,26,41,62}` | **Book** | finite leaf | 89 | 45,905 | 0.363 |
| 43 | `{16,26,43,62,98}` | **Book** | finite leaf | 95 | 4,571,992 | 38.290 |
| 44 | `{16,26,44,62,98}` | **Book** | reply 19 → `{16,19,26,44,62}` | 177 | 112,852 | 0.619 |
| 46 | `{16,26,46}` | **Book** | reply 17 → `{16,17,26,46}` | 159 | 47,285 | 0.311 |
| 50 | `{16,26,50,62}` | **Book** | reply 29 → `{16,26,29,50,62}` | 171 | 833,424 | 5.525 |
| 51 | `{16,26,51,62,98}` | **Book** | finite leaf | 95 | 9,164,251 | 77.109 |
| 54 | `{16,26,54,62,98}` | **Book** | reply 33 → `{16,26,33,54,62}` | 177 | 1,191,332 | 7.292 |
| 56 | `{16,26,56,62}` | **Book** | reply 97 → `{16,26,56,62,97}` | 171 | 25,236,025 | 280.739 |
| 59 | `{16,26,59,62,98}` | **Book** | reply 47 → `{16,26,47,59,62,98}` | 183 | 4,458,041 | 32.691 |
| 60 | `{16,26,60,62,98}` | **Book** | reply 27 → `{16,26,27,60,62,98}` | 183 | 611,082 | 3.678 |
| 66 | `{16,26,62,66}` | finite witness, not yet in the Book | reply 263 → `{16,26,62,66,263}` | | | |
| 67 | `{16,26,62,67,98}` | **Book** | finite leaf | 95 | 2,049,906 | 14.132 |
| 70 | `{16,26,62,70,98}` | finite witness, not yet in the Book | reply 169 → `{16,26,62,70,98,169}` | | | |
| 72 | `{16,26,62,72}` | **Book** | reply 107 → `{16,26,62,72,107}` | 174 | 50,192,273 | 612.178 |
| 76 | `{16,26,62,76,98}` | **Book** | reply 43 → `{16,26,43,62,76,98}` | 183 | 4,294,839 | 30.759 |
| 82 | `{16,26,62,82}` | **Book** | reply 27 → `{16,26,27,62,82}` | 171 | 732,964 | 4.346 |
| 86 | `{16,26,62,86,98}` | **Book** | reply 129 → `{16,26,62,86,98,129}` | 186 | 68,758,240 | 813.610 |
| 92 | `{16,26,62,92,98}` | finite witness, not yet in the Book | reply 139 → `{16,26,62,92,98,139}` | | | |
| 102 | `{16,26,62,98,102}` | **Book** | reply 95 → `{16,26,62,95,98,102}` | 187 | 44,985,582 | 549.594 |
| 108 | `{16,26,62,98,108}` | finite witness, not yet in the Book | reply 213 → `{16,26,62,98,108,213}` | | | |
| 118 | `{16,26,62,98,118}` | finite witness, not yet in the Book | reply 167 → `{16,26,62,98,118,167}` | | | |
| 134 | `{16,26,62,98,134}` | **Book** | reply 85 → `{16,26,62,85,98,134}` | 187 | 37,192,385 | 417.194 |
