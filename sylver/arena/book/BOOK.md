# The Book

The cheapest-to-check known certificate for each public result. Every entry was re-verified
by the fixed verifier with a fresh memo; *states* is the verifier's deterministic
evaluated-state count, identical in every run, and *V* the median verification CPU seconds
on the recording machine (for information). The entry of record minimizes the checking cost
(C+100)*(states/100,000+1): the agreed score's shape with verification time replaced by the
verifier's own work, so timing noise never changes the record. These are independent
certificates of public results, not new mathematics.

| Target | Outcome | Proof | C | States | V (s) | Checking cost | Entries | Found by |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `{2}` | N | edge 3 | 128 | 1 | 0.179 | 228 | 1 | golf-witness |
| `{4,6}` | P | cover | 225 | 1 | 0.152 | 325 | 1 | curator certificate |
| `{4,26}` | N | edge 6 | 286 | 1 | 0.150 | 386 | 1 | curator certificate |
| `{5,16}` | N | finite | 75 | 62 | 0.171 | 175 | 2 | golf-root |
| `{10,16}` | N | edge 9 | 144 | 213 | 0.150 | 245 | 1 | curator certificate |
| `{3,16,26}` | N | finite | 81 | 2 | 0.171 | 181 | 2 | golf-root |
| `{6,16,26}` | N | edge 7 | 146 | 21 | 0.150 | 246 | 1 | curator certificate |
| `{7,16,26}` | N | finite | 81 | 31 | 0.175 | 181 | 2 | golf-root |
| `{8,26,62}` | N | edge 49 | 155 | 18,604 | 0.287 | 302 | 1 | curator certificate |
| `{9,16,26}` | N | finite | 81 | 340 | 0.174 | 182 | 2 | golf-root |
| `{14,16,26}` | N | edge 23 | 159 | 5,559 | 0.190 | 273 | 1 | curator certificate |
| `{15,16,26}` | N | finite | 83 | 10,911 | 0.233 | 203 | 2 | golf-root |
| `{16,18,26}` | N | edge 5 | 150 | 50 | 0.177 | 250 | 1 | golf-witness |
| `{16,20,26}` | N | edge 14 | 2181 | 11,114 | 0.225 | 2,535 | 1 | curator certificate |
| `{16,23,26}` | N | finite | 83 | 10,306 | 0.248 | 202 | 2 | golf-root |
| `{16,26,30}` | N | edge 73 | 159 | 2,378,741 | 28.299 | 6,420 | 1 | golf-witness |
| `{16,26,46}` | N | edge 17 | 159 | 47,285 | 0.311 | 381 | 1 | golf-witness |
| `{11,16,26,62}` | N | finite | 89 | 4,089 | 0.196 | 197 | 2 | golf-root |
| `{16,17,26,62}` | N | finite | 89 | 49,212 | 0.461 | 282 | 2 | golf-root |
| `{16,22,26,62}` | N | edge 15 | 165 | 5,956 | 0.209 | 281 | 1 | golf-witness |
| `{16,24,26,62}` | N | edge 15 | 165 | 7,377 | 0.181 | 285 | 1 | curator certificate |
| `{16,25,26,62}` | N | finite | 89 | 186,709 | 1.521 | 542 | 2 | golf-root |
| `{16,26,28,62}` | N | edge 25 | 171 | 105,133 | 0.894 | 556 | 1 | golf-witness |
| `{16,26,33,62}` | N | finite | 89 | 1,533,942 | 18.556 | 3,088 | 2 | golf-root |
| `{16,26,34,62}` | N | edge 39 | 171 | 800,890 | 5.902 | 2,441 | 1 | golf-witness |
| `{16,26,40,62}` | N | edge 11 | 165 | 3,740 | 0.157 | 275 | 1 | golf-witness |
| `{16,26,41,62}` | N | finite | 89 | 45,905 | 0.363 | 276 | 2 | golf-root |
| `{16,26,50,62}` | N | edge 29 | 171 | 833,424 | 5.525 | 2,530 | 1 | golf-witness |
| `{16,26,56,62}` | N | edge 97 | 171 | 25,236,025 | 280.739 | 68,661 | 1 | curator certificate |
| `{16,26,62,72}` | N | edge 107 | 174 | 50,192,273 | 612.178 | 137,801 | 1 | curator certificate |
| `{16,26,62,82}` | N | edge 27 | 171 | 732,964 | 4.346 | 2,257 | 1 | golf-witness |
| `{16,19,26,62,98}` | N | finite | 95 | 67,254 | 0.623 | 326 | 2 | golf-root |
| `{16,26,27,62,98}` | N | finite | 95 | 61,349 | 0.565 | 315 | 2 | golf-root |
| `{16,26,35,62,98}` | N | edge 24 | 177 | 209,885 | 1.278 | 858 | 2 | golf-witness |
| `{16,26,38,62,98}` | N | edge 55 | 183 | 3,240,895 | 27.461 | 9,455 | 1 | golf-witness |
| `{16,26,43,62,98}` | N | finite | 95 | 4,571,992 | 38.290 | 9,110 | 2 | golf-root |
| `{16,26,44,62,98}` | N | edge 19 | 177 | 112,852 | 0.619 | 590 | 1 | golf-witness |
| `{16,26,51,62,98}` | N | finite | 95 | 9,164,251 | 77.109 | 18,065 | 2 | golf-root |
| `{16,26,54,62,98}` | N | edge 33 | 177 | 1,191,332 | 7.292 | 3,577 | 1 | golf-witness |
| `{16,26,59,62,98}` | N | edge 47 | 183 | 4,458,041 | 32.691 | 12,899 | 2 | golf-witness |
| `{16,26,60,62,98}` | N | edge 27 | 183 | 611,082 | 3.678 | 2,012 | 1 | golf-witness |
| `{16,26,62,67,98}` | N | finite | 95 | 2,049,906 | 14.132 | 4,192 | 2 | golf-root |
| `{16,26,62,76,98}` | N | edge 43 | 183 | 4,294,839 | 30.759 | 12,437 | 1 | golf-witness |
| `{16,26,62,86,98}` | N | edge 129 | 186 | 68,758,240 | 813.610 | 196,935 | 1 | curator certificate |
| `{16,26,62,98,102}` | N | edge 95 | 187 | 44,985,582 | 549.594 | 129,396 | 1 | golf-root |
| `{16,26,62,98,134}` | N | edge 85 | 187 | 37,192,385 | 417.194 | 107,029 | 1 | golf-root |
| `{16,26,28,30,38,79}` | P | finite | 101 | 448,489 | 4.818 | 1,102 | 1 | golf-root |
| `{16,26,33,62,89,102}` | P | finite | 103 | 1,721,485 | 14.809 | 3,698 | 1 | golf-root |
| `{16,26,62,89,98,102}` | N | edge 33 | 193 | 1,721,485 | 12.172 | 5,337 | 2 | golf-witness |
| `{16,26,70,82,83,88,133,137}` | N | edge 27 | 205 | 802,672 | 5.362 | 2,753 | 2 | golf-witness |
| `{16,26,34,38,40,115,151,159}` | P | finite | 119 | 1,390,816 | 16.331 | 3,265 | 1 | golf-root |
| `{16,26,30,38,109,123,127,137}` | P | finite | 121 | 1,876,804 | 21.917 | 4,369 | 1 | golf-root |
| `{16,20,26,28,38,111,121,129,135}` | P | finite | 127 | 169,082 | 2.094 | 611 | 1 | golf-root |
| `{16,26,30,36,38,50,115,125,139,159}` | N | finite | 133 | 759 | 0.163 | 235 | 2 | golf-root |
| `{16,26,38,44,46,56,111,129,131,133}` | P | finite | 133 | 3,330,318 | 35.817 | 7,993 | 1 | golf-root |
| `{16,26,82,86,88,93,129,149,163,169}` | N | edge 28 | 217 | 2,657,828 | 21.576 | 8,742 | 2 | golf-witness |
| `{16,26,34,38,40,117,123,125,127,131}` | N | finite | 135 | 688,662 | 6.984 | 1,853 | 2 | golf-root |
| `{16,26,38,44,50,113,141,147,149,159}` | P | finite | 135 | 4,797,858 | 56.770 | 11,510 | 1 | golf-root |
| `{16,26,30,36,38,40,44,113,121,123,127,131}` | N | finite | 147 | 370,334 | 2.596 | 1,162 | 2 | golf-root |
| `{16,26,36,38,44,56,66,119,137,139,141,147}` | N | finite | 147 | 2,358,078 | 22.944 | 6,071 | 2 | golf-root |

Certificates are in `certificates/SHA256.json`; `python -m sylver.arena book verify` replays them.
How entries are admitted and priced: [sylver/arena/README.md](../README.md#certificate-golf-and-the-book-16).
