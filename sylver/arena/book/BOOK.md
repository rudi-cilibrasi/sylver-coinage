# The Book

The cheapest-to-check known certificate for each public result. Every entry was re-verified
by the fixed verifier with a fresh memo, three times; *states* is its deterministic
evaluated-state count and *V* the median verification CPU seconds on the recording machine.
The entry of record minimizes (C+100)*(V+1), which prices checking, not discovery.
These are independent certificates of public results, not new mathematics.

| Target | Outcome | Proof | C | States | V (s) | (C+100)(V+1) | Entries | Found by |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `{16,26,62,98,102}` | N | edge 95 | 187 | 44,985,582 | 590.572 | 169781 | 1 | golf-witness |
| `{16,26,62,98,134}` | N | edge 85 | 187 | 37,192,385 | 464.943 | 133726 | 1 | golf-witness |
| `{16,26,28,30,38,79}` | P | finite | 101 | 448,489 | 4.678 | 1141 | 1 | golf-probe |
| `{16,26,33,62,89,102}` | P | finite | 103 | 1,721,485 | 14.162 | 3078 | 1 | golf-witness |
| `{16,26,62,89,98,102}` | N | edge 33 | 193 | 1,721,485 | 11.669 | 3712 | 1 | golf-witness |
| `{16,26,70,82,83,88,133,137}` | N | edge 27 | 205 | 802,672 | 8.469 | 2888 | 1 | golf-witness |
| `{16,26,34,38,40,115,151,159}` | P | finite | 119 | 1,390,816 | 15.274 | 3564 | 1 | golf-root |
| `{16,26,30,38,109,123,127,137}` | P | finite | 121 | 1,876,804 | 23.585 | 5433 | 1 | golf-root |
| `{16,20,26,28,38,111,121,129,135}` | P | finite | 127 | 169,082 | 1.681 | 609 | 1 | golf-root |
| `{16,26,30,36,38,50,115,125,139,159}` | N | finite | 133 | 759 | 0.186 | 276 | 1 | golf-root |
| `{16,26,38,44,46,56,111,129,131,133}` | P | finite | 133 | 3,330,318 | 30.488 | 7337 | 1 | golf-root |
| `{16,26,82,86,88,93,129,149,163,169}` | N | finite | 133 | 3,747,484 | 40.731 | 9723 | 1 | golf-root |
| `{16,26,34,38,40,117,123,125,127,131}` | N | finite | 135 | 688,662 | 6.946 | 1867 | 1 | golf-root |
| `{16,26,38,44,50,113,141,147,149,159}` | P | finite | 135 | 4,797,858 | 51.885 | 12428 | 1 | golf-probe |
| `{16,26,30,36,38,40,44,113,121,123,127,131}` | N | finite | 147 | 370,334 | 3.479 | 1106 | 1 | golf-root |
| `{16,26,36,38,44,56,66,119,137,139,141,147}` | N | finite | 147 | 2,358,078 | 23.666 | 6092 | 1 | golf-root |

Certificates are in `certificates/SHA256.json`; `python -m sylver.arena book verify` replays them. The golf pilot that produced these entries is recorded in [../data/golf/REPORT.md](../data/golf/REPORT.md).
