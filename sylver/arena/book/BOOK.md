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
