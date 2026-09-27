# Certificate golf pilot

Every target is a public database result, so golf measures how cheaply a program can
*certify* a known outcome, not discovery. Hints are untrusted: every certificate here was
replayed by the fixed verifier with a fresh memo. S=(C+100)*(T+1), lower is better;
T is discovery plus verification CPU seconds. golf-blind is the hint-free control; the
interleaved search baseline is the pre-existing arena policy, whose fixed 0.6 s query
slices are far below these targets' root searches. No new mathematics is claimed.

## Median S per target

| Target | Tier | Outcome | Distinct certificates | golf-blind | golf-probe | golf-root | golf-witness | interleaved |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `{16,20,26,28,38,111,121,129,135}` | A | P | 1 | 932 | 741 | 704 | 711 | — |
| `{16,26,28,30,38,79}` | A | P | 1 | 1908 | 1095 | 1103 | 1259 | — |
| `{16,26,30,36,38,40,44,113,121,123,127,131}` | A | N | 2 | 2083 | 2408 | 1212 | 1698 | — |
| `{16,26,30,36,38,50,115,125,139,159}` | A | N | 2 | 321 | 402 | 394 | 534 | — |
| `{16,26,30,38,109,123,127,137}` | A | P | 1 | 8678 | 5288 | 5172 | 5248 | — |
| `{16,26,34,38,40,117,123,125,127,131}` | A | N | 2 | 3768 | 5407 | 1812 | 2322 | — |
| `{16,26,34,38,40,115,151,159}` | B | P | 1 | 6801 | 4001 | 3685 | 3511 | — |
| `{16,26,36,38,44,56,66,119,137,139,141,147}` | B | N | 2 | 13548 | 20652 | 7248 | 12267 | — |
| `{16,26,38,44,46,56,111,129,131,133}` | B | P | 1 | 17199 | 9297 | 10260 | 10189 | — |
| `{16,26,38,44,50,113,141,147,149,159}` | B | P | 1 | 25311 | 15346 | 15164 | 14912 | — |
| `{16,26,70,82,83,88,133,137}` | B | N | 2 | 6969 | 8395 | 3649 | 2992 | — |
| `{16,26,82,86,88,93,129,149,163,169}` | B | N | 2 | 20473 | 29074 | 11096 | 10876 | — |
| `{16,26,33,62,89,102}` | C | P | 1 | 7553 | 4156 | 3026 | 3696 | — |
| `{16,26,62,89,98,102}` | C | N | 2 | 27913 | 19394 | 15328 | 5438 | — |
| `{16,26,62,98,102}` | C | N | 1 | — | 185928 | 188165 | 181101 | — |
| `{16,26,62,98,134}` | C | N | 1 | — | 134726 | 134788 | 126408 | — |

## Lowest median S where the certificates differ

7 of 16 targets received more than one distinct certificate; on the
others every competitor submitted the same proof, so their ordering is timing noise.

- golf-blind: 1 of 7 targets
- golf-probe: 0 of 7 targets
- golf-root: 3 of 7 targets
- golf-witness: 3 of 7 targets
- interleaved: 0 of 7 targets

## Findings and decision (curator's summary, not generated)

This run used the reviewed code: the hint-free `golf-blind` control, a
`golf-probe` that submits directly when there is only one option, and a
Book that admits every distinct valid certificate and picks each target's
entry of record by deterministic checking cost. It ran 200 episodes under
one execution profile on a shared, heavily loaded workstation (three
concurrent episodes beside other campaign work), so compare scores only
within this run.

1. **Hints are decisive for gcd-two targets and roughly halve the work on
   finite ones.** On the finite targets, `golf-blind` must compute the
   outcome it then certifies, and its T was 1.5–2.6 times `golf-root`'s on
   13 of 14. It certified neither gcd-two W target within its three-reply
   search, while every hinted strategy did. On the smallest target (a
   759-state root search), loading the 308,322-row hint file (about 0.3 s)
   cost more than the whole check, and `golf-blind` had the lowest S.
2. **Structure matters when the database offers a much cheaper witness.**
   Seven targets received two distinct certificates (a root leaf and a
   witness edge). The witness edge had the lowest median S on three, by up
   to **2.8 times** on `{16,26,62,89,98,102}` (verifier root search
   6,382,154 states; hinted witness 33, 1,721,485 states). The root leaf won
   three, where the witness saved too little checking to pay for its extra
   bytes; `golf-blind` won the smallest.
3. **Nine targets offered no choice.** On P targets and the gcd-two W
   targets every strategy submitted the same certificate, so their ordering
   in the tables is timing noise.
4. **Probing does not pay** when measuring a candidate costs about as much
   as verifying it: `golf-probe` never had the lowest median S where
   certificates differed.
5. **The search baseline cannot compete here.** `interleaved` certified
   nothing: its fixed 0.6 s query slices are far below these targets' root
   searches (1–85 s). This reflects its toy-task tuning, not the value of
   hints; `golf-blind` is the fair hint-free comparison.

**Decision: continue, with cost prediction as the next competitor.** The
Book now holds both certificate types for every target with a choice, each
with its deterministic state count, which is exactly the data a cost-aware
golfer needs to predict checking cost without measuring by solving.
External programs and model-driven agents can compete through the same
protocol and pinned hints.

The Book seeded by this pilot is [sylver/arena/book/BOOK.md](../../book/BOOK.md); per-run leaderboards follow.

# Golf leaderboards

Scores are compared only within an identical target, snapshot, verifier, and execution profile.

C is canonical UTF-8 proof bytes; T is discovery + verification CPU seconds. Lower S=(C+100)*(T+1) is better.

## Target {16,26,34,38,40,117,123,125,127,131} — 151c27f1d5439bba

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | N | 135 | 0.478200 | 6.152219 | 6.630419 | 1793.148407 | 7.491728 |
| golf-root | valid | N | 135 | 0.378124 | 6.331449 | 6.709573 | 1811.749606 | 7.502048 |
| golf-witness | valid | N | 263 | 0.352968 | 3.711207 | 4.064175 | 1838.295507 | 7.516594 |
| golf-root | valid | N | 135 | 0.571999 | 7.848923 | 8.420922 | 2213.916635 | 7.702518 |
| golf-witness | valid | N | 263 | 0.469248 | 4.926541 | 5.395789 | 2321.671438 | 7.750043 |
| golf-witness | valid | N | 263 | 0.552959 | 5.317916 | 5.870875 | 2494.127518 | 7.821694 |
| golf-blind | valid | N | 135 | 5.219765 | 4.957001 | 10.176766 | 2626.540004 | 7.873423 |
| golf-blind | valid | N | 135 | 7.612926 | 7.421836 | 15.034762 | 3768.169159 | 8.234345 |
| golf-blind | valid | N | 135 | 7.670328 | 7.417683 | 15.088011 | 3780.682617 | 8.237660 |
| golf-probe | valid | N | 135 | 13.049113 | 7.508027 | 20.557139 | 5065.927777 | 8.530293 |
| golf-probe | valid | N | 263 | 9.395070 | 4.500636 | 13.895706 | 5407.141208 | 8.595476 |
| golf-probe | valid | N | 263 | 10.581299 | 4.964937 | 15.546236 | 6006.283660 | 8.700561 |
| interleaved | unsolved | unknown | — | 7.960583 | — | 7.960583 | — | — |
| interleaved | unsolved | unknown | — | 8.111979 | — | 8.111979 | — | — |
| interleaved | unsolved | unknown | — | 8.337334 | — | 8.337334 | — | — |

golf-blind: 3/3 valid; S min/median/max = 2626.540004/3768.169159/3780.682617; stdev = 662.761758.
golf-probe: 3/3 valid; S min/median/max = 5065.927777/5407.141208/6006.283660; stdev = 476.037020.
golf-root: 3/3 valid; S min/median/max = 1793.148407/1811.749606/2213.916635; stdev = 237.742938.
golf-witness: 3/3 valid; S min/median/max = 1838.295507/2321.671438/2494.127518; stdev = 339.977700.
interleaved: 0/3 valid.

## Target {16,26,62,98,102} — 3bd08ef71d1d7176

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | N | 187 | 0.312898 | 629.699363 | 630.012261 | 181100.518985 | 12.106808 |
| golf-probe | valid | N | 187 | 0.315090 | 646.515972 | 646.831063 | 185927.515068 | 12.133112 |
| golf-root | valid | N | 187 | 0.347079 | 654.278418 | 654.625496 | 188164.517448 | 12.145072 |
| golf-blind | unsolved | unknown | — | 0.193978 | — | 0.193978 | — | — |
| interleaved | unsolved | unknown | — | 8.046473 | — | 8.046473 | — | — |

golf-blind: 0/1 valid.
golf-probe: 1/1 valid; S min/median/max = 185927.515068/185927.515068/185927.515068; stdev = 0.000000.
golf-root: 1/1 valid; S min/median/max = 188164.517448/188164.517448/188164.517448; stdev = 0.000000.
golf-witness: 1/1 valid; S min/median/max = 181100.518985/181100.518985/181100.518985; stdev = 0.000000.
interleaved: 0/1 valid.

## Target {16,26,62,98,134} — 47bac9f225e735d9

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | N | 187 | 0.428550 | 439.018976 | 439.447525 | 126408.439805 | 11.747274 |
| golf-probe | valid | N | 187 | 0.421029 | 468.006650 | 468.427679 | 134725.743932 | 11.810996 |
| golf-root | valid | N | 187 | 0.545981 | 468.098813 | 468.644794 | 134788.055889 | 11.811459 |
| golf-blind | unsolved | unknown | — | 0.153416 | — | 0.153416 | — | — |
| interleaved | unsolved | unknown | — | 7.862574 | — | 7.862574 | — | — |

golf-blind: 0/1 valid.
golf-probe: 1/1 valid; S min/median/max = 134725.743932/134725.743932/134725.743932; stdev = 0.000000.
golf-root: 1/1 valid; S min/median/max = 134788.055889/134788.055889/134788.055889; stdev = 0.000000.
golf-witness: 1/1 valid; S min/median/max = 126408.439805/126408.439805/126408.439805; stdev = 0.000000.
interleaved: 0/1 valid.

## Target {16,26,36,38,44,56,66,119,137,139,141,147} — 5795d5873ed91d07

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | N | 147 | 0.479689 | 24.472051 | 24.951741 | 6410.079917 | 8.765627 |
| golf-root | valid | N | 147 | 0.484439 | 27.857676 | 28.342115 | 7247.502303 | 8.888412 |
| golf-root | valid | N | 147 | 0.506175 | 31.321186 | 31.827361 | 8108.358050 | 9.000651 |
| golf-witness | valid | N | 282 | 0.365267 | 27.517042 | 27.882309 | 11033.041972 | 9.308650 |
| golf-witness | valid | N | 282 | 0.503839 | 30.608916 | 31.112755 | 12267.072291 | 9.414674 |
| golf-witness | valid | N | 282 | 0.532086 | 31.809252 | 32.341337 | 12736.390922 | 9.452219 |
| golf-blind | valid | N | 147 | 29.469296 | 21.782057 | 51.251353 | 12906.084175 | 9.465454 |
| golf-blind | valid | N | 147 | 30.497987 | 23.350869 | 53.848856 | 13547.667472 | 9.513970 |
| golf-blind | valid | N | 147 | 29.633221 | 28.167287 | 57.800508 | 14523.725560 | 9.583539 |
| golf-probe | valid | N | 147 | 52.776266 | 27.204726 | 79.980992 | 20002.305087 | 9.903603 |
| golf-probe | valid | N | 147 | 56.049830 | 26.562262 | 82.612092 | 20652.186667 | 9.935576 |
| golf-probe | valid | N | 147 | 60.844169 | 28.298930 | 89.143099 | 22265.345330 | 10.010787 |
| interleaved | unsolved | unknown | — | 8.103136 | — | 8.103136 | — | — |
| interleaved | unsolved | unknown | — | 8.012229 | — | 8.012229 | — | — |
| interleaved | unsolved | unknown | — | 8.160546 | — | 8.160546 | — | — |

golf-blind: 3/3 valid; S min/median/max = 12906.084175/13547.667472/14523.725560; stdev = 814.563499.
golf-probe: 3/3 valid; S min/median/max = 20002.305087/20652.186667/22265.345330; stdev = 1165.187974.
golf-root: 3/3 valid; S min/median/max = 6410.079917/7247.502303/8108.358050; stdev = 849.166011.
golf-witness: 3/3 valid; S min/median/max = 11033.041972/12267.072291/12736.390922; stdev = 879.818964.
interleaved: 0/3 valid.

## Target {16,26,30,36,38,50,115,125,139,159} — 6a8759c7dbf8e5a2

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-blind | valid | N | 133 | 0.186811 | 0.187964 | 0.374775 | 320.322658 | 5.769329 |
| golf-blind | valid | N | 133 | 0.191467 | 0.185946 | 0.377413 | 320.937221 | 5.771246 |
| golf-blind | valid | N | 133 | 0.207791 | 0.196804 | 0.404595 | 327.270691 | 5.790788 |
| golf-root | valid | N | 133 | 0.495273 | 0.177845 | 0.673118 | 389.836384 | 5.965727 |
| golf-root | valid | N | 133 | 0.504162 | 0.187900 | 0.692062 | 394.250365 | 5.976986 |
| golf-root | valid | N | 133 | 0.508085 | 0.186403 | 0.694487 | 394.815559 | 5.978419 |
| golf-probe | valid | N | 133 | 0.511668 | 0.186263 | 0.697932 | 395.618044 | 5.980449 |
| golf-probe | valid | N | 133 | 0.545408 | 0.179019 | 0.724427 | 401.791392 | 5.995933 |
| golf-probe | valid | N | 133 | 0.601003 | 0.217588 | 0.818591 | 423.731610 | 6.049100 |
| golf-witness | valid | N | 210 | 0.436395 | 0.182197 | 0.618592 | 501.763424 | 6.218129 |
| golf-witness | valid | N | 210 | 0.534450 | 0.188641 | 0.723091 | 534.158177 | 6.280692 |
| golf-witness | valid | N | 210 | 0.533985 | 0.192984 | 0.726969 | 535.360432 | 6.282940 |
| interleaved | unsolved | unknown | — | 7.645520 | — | 7.645520 | — | — |
| interleaved | unsolved | unknown | — | 8.103546 | — | 8.103546 | — | — |
| interleaved | unsolved | unknown | — | 8.103141 | — | 8.103141 | — | — |

golf-blind: 3/3 valid; S min/median/max = 320.322658/320.937221/327.270691; stdev = 3.846333.
golf-probe: 3/3 valid; S min/median/max = 395.618044/401.791392/423.731610; stdev = 14.775295.
golf-root: 3/3 valid; S min/median/max = 389.836384/394.250365/394.815559; stdev = 2.726257.
golf-witness: 3/3 valid; S min/median/max = 501.763424/534.158177/535.360432; stdev = 19.059662.
interleaved: 0/3 valid.

## Target {16,26,70,82,83,88,133,137} — 758b66651e42b499

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | N | 205 | 0.369328 | 6.639882 | 7.009209 | 2442.808880 | 7.800904 |
| golf-witness | valid | N | 205 | 0.480785 | 8.328885 | 8.809671 | 2991.949536 | 8.003680 |
| golf-witness | valid | N | 205 | 0.504120 | 8.728109 | 9.232229 | 3120.829868 | 8.045854 |
| golf-root | valid | N | 117 | 0.368347 | 13.198205 | 13.566551 | 3160.941658 | 8.058625 |
| golf-root | valid | N | 117 | 0.508416 | 15.307833 | 15.816248 | 3649.125921 | 8.202243 |
| golf-root | valid | N | 117 | 0.517071 | 16.064004 | 16.581075 | 3815.093333 | 8.246720 |
| golf-blind | valid | N | 117 | 14.983134 | 15.747686 | 30.730819 | 6885.587780 | 8.837186 |
| golf-blind | valid | N | 117 | 15.664891 | 15.451323 | 31.116214 | 6969.218520 | 8.849258 |
| golf-blind | valid | N | 117 | 16.219395 | 15.334652 | 31.554048 | 7064.228334 | 8.862799 |
| golf-probe | valid | N | 117 | 20.532219 | 14.858436 | 35.390656 | 7896.772292 | 8.974209 |
| golf-probe | valid | N | 205 | 17.702200 | 8.821308 | 26.523508 | 8394.669893 | 9.035352 |
| golf-probe | valid | N | 205 | 20.276886 | 8.504552 | 28.781439 | 9083.338761 | 9.114197 |
| interleaved | unsolved | unknown | — | 8.199472 | — | 8.199472 | — | — |
| interleaved | unsolved | unknown | — | 8.067234 | — | 8.067234 | — | — |
| interleaved | unsolved | unknown | — | 8.019373 | — | 8.019373 | — | — |

golf-blind: 3/3 valid; S min/median/max = 6885.587780/6969.218520/7064.228334; stdev = 89.380659.
golf-probe: 3/3 valid; S min/median/max = 7896.772292/8394.669893/9083.338761; stdev = 595.833704.
golf-root: 3/3 valid; S min/median/max = 3160.941658/3649.125921/3815.093333; stdev = 340.044965.
golf-witness: 3/3 valid; S min/median/max = 2442.808880/2991.949536/3120.829868; stdev = 360.064361.
interleaved: 0/3 valid.

## Target {16,20,26,28,38,111,121,129,135} — 7dc4c5f620bea400

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | P | 127 | 0.492249 | 1.428800 | 1.921049 | 663.078094 | 6.496893 |
| golf-root | valid | P | 127 | 0.479581 | 1.622259 | 2.101840 | 704.117652 | 6.556945 |
| golf-witness | valid | P | 127 | 0.474715 | 1.642943 | 2.117658 | 707.708441 | 6.562032 |
| golf-probe | valid | P | 127 | 0.476350 | 1.645329 | 2.121679 | 708.621189 | 6.563321 |
| golf-witness | valid | P | 127 | 0.498410 | 1.633296 | 2.131707 | 710.897378 | 6.566528 |
| golf-root | valid | P | 127 | 0.497536 | 1.761056 | 2.258592 | 739.700301 | 6.606245 |
| golf-witness | valid | P | 127 | 0.506159 | 1.759243 | 2.265402 | 741.246301 | 6.608333 |
| golf-probe | valid | P | 127 | 0.507295 | 1.758431 | 2.265726 | 741.319735 | 6.608432 |
| golf-probe | valid | P | 127 | 0.489101 | 1.790501 | 2.279601 | 744.469508 | 6.612672 |
| golf-blind | valid | P | 127 | 1.480150 | 1.397648 | 2.877798 | 880.260203 | 6.780218 |
| golf-blind | valid | P | 127 | 1.340345 | 1.765098 | 3.105443 | 931.935541 | 6.837264 |
| golf-blind | valid | P | 127 | 1.791898 | 1.828720 | 3.620618 | 1048.880349 | 6.955479 |
| interleaved | unsolved | unknown | — | 7.230522 | — | 7.230522 | — | — |
| interleaved | unsolved | unknown | — | 7.507481 | — | 7.507481 | — | — |
| interleaved | unsolved | unknown | — | 7.450145 | — | 7.450145 | — | — |

golf-blind: 3/3 valid; S min/median/max = 880.260203/931.935541/1048.880349; stdev = 86.389797.
golf-probe: 3/3 valid; S min/median/max = 708.621189/741.319735/744.469508; stdev = 19.850348.
golf-root: 3/3 valid; S min/median/max = 663.078094/704.117652/739.700301; stdev = 38.343476.
golf-witness: 3/3 valid; S min/median/max = 707.708441/710.897378/741.246301; stdev = 18.511323.
interleaved: 0/3 valid.

## Target {16,26,28,30,38,79} — a0380ff0c0638a3e

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-probe | valid | P | 101 | 0.457754 | 3.695910 | 4.153664 | 1035.886478 | 6.943013 |
| golf-root | valid | P | 101 | 0.424244 | 3.889625 | 4.313870 | 1068.087798 | 6.973625 |
| golf-probe | valid | P | 101 | 0.377745 | 4.069755 | 4.447500 | 1094.947413 | 6.998462 |
| golf-root | valid | P | 101 | 0.373804 | 4.111575 | 4.485379 | 1102.561125 | 7.005391 |
| golf-witness | valid | P | 101 | 0.476706 | 4.136545 | 4.613250 | 1128.263304 | 7.028435 |
| golf-witness | valid | P | 101 | 0.381778 | 4.879840 | 5.261618 | 1258.585212 | 7.137744 |
| golf-probe | valid | P | 101 | 0.490179 | 4.779324 | 5.269503 | 1260.170159 | 7.139002 |
| golf-witness | valid | P | 101 | 0.514342 | 4.836435 | 5.350777 | 1276.506132 | 7.151882 |
| golf-root | valid | P | 101 | 0.515709 | 4.917816 | 5.433525 | 1293.138525 | 7.164828 |
| golf-blind | valid | P | 101 | 3.771315 | 4.718287 | 8.489602 | 1907.409960 | 7.553502 |
| golf-blind | valid | P | 101 | 4.203212 | 4.288067 | 8.491278 | 1907.746962 | 7.553678 |
| golf-blind | valid | P | 101 | 5.039546 | 4.837079 | 9.876625 | 2186.201627 | 7.689921 |
| interleaved | unsolved | unknown | — | 7.392178 | — | 7.392178 | — | — |
| interleaved | unsolved | unknown | — | 7.564300 | — | 7.564300 | — | — |
| interleaved | unsolved | unknown | — | 7.701086 | — | 7.701086 | — | — |

golf-blind: 3/3 valid; S min/median/max = 1907.409960/1907.746962/2186.201627; stdev = 160.863248.
golf-probe: 3/3 valid; S min/median/max = 1035.886478/1094.947413/1260.170159; stdev = 116.253974.
golf-root: 3/3 valid; S min/median/max = 1068.087798/1102.561125/1293.138525; stdev = 121.213300.
golf-witness: 3/3 valid; S min/median/max = 1128.263304/1258.585212/1276.506132; stdev = 80.912396.
interleaved: 0/3 valid.

## Target {16,26,38,44,46,56,111,129,131,133} — a4adca4e321bcf35

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-probe | valid | P | 133 | 0.481704 | 33.909734 | 34.391438 | 8246.205053 | 9.017508 |
| golf-witness | valid | P | 133 | 0.500230 | 34.406623 | 34.906853 | 8366.296835 | 9.031967 |
| golf-root | valid | P | 133 | 0.502889 | 36.989712 | 37.492602 | 8968.776229 | 9.101505 |
| golf-probe | valid | P | 133 | 0.475865 | 38.426987 | 38.902851 | 9297.364392 | 9.137486 |
| golf-probe | valid | P | 133 | 0.498330 | 41.943249 | 42.441579 | 10121.887998 | 9.222455 |
| golf-witness | valid | P | 133 | 0.428598 | 42.299742 | 42.728341 | 10188.703338 | 9.229035 |
| golf-root | valid | P | 133 | 0.487942 | 42.547812 | 43.035754 | 10260.330711 | 9.236040 |
| golf-root | valid | P | 133 | 0.483350 | 43.338881 | 43.822230 | 10443.579675 | 9.253743 |
| golf-witness | valid | P | 133 | 0.437081 | 44.373137 | 44.810219 | 10673.780993 | 9.275546 |
| golf-blind | valid | P | 133 | 34.523906 | 35.844287 | 70.368192 | 16628.788819 | 9.718891 |
| golf-blind | valid | P | 133 | 36.788774 | 36.025804 | 72.814579 | 17198.796796 | 9.752595 |
| golf-blind | valid | P | 133 | 42.654809 | 38.142854 | 80.797663 | 19058.855561 | 9.855287 |
| interleaved | unsolved | unknown | — | 8.048038 | — | 8.048038 | — | — |
| interleaved | unsolved | unknown | — | 8.107759 | — | 8.107759 | — | — |
| interleaved | unsolved | unknown | — | 8.104164 | — | 8.104164 | — | — |

golf-blind: 3/3 valid; S min/median/max = 16628.788819/17198.796796/19058.855561; stdev = 1270.823360.
golf-probe: 3/3 valid; S min/median/max = 8246.205053/9297.364392/10121.887998; stdev = 940.120705.
golf-root: 3/3 valid; S min/median/max = 8968.776229/10260.330711/10443.579675; stdev = 803.817804.
golf-witness: 3/3 valid; S min/median/max = 8366.296835/10188.703338/10673.780993; stdev = 1216.617506.
interleaved: 0/3 valid.

## Target {16,26,34,38,40,115,151,159} — aa1972357d7da594

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | P | 119 | 0.408095 | 13.911985 | 14.320080 | 3355.097547 | 8.118236 |
| golf-probe | valid | P | 119 | 0.478484 | 14.439311 | 14.917795 | 3485.997160 | 8.156509 |
| golf-witness | valid | P | 119 | 0.479582 | 14.552299 | 15.031881 | 3510.981940 | 8.163651 |
| golf-witness | valid | P | 119 | 0.480714 | 14.606227 | 15.086941 | 3523.040076 | 8.167080 |
| golf-root | valid | P | 119 | 0.520140 | 14.599086 | 15.119227 | 3530.110683 | 8.169085 |
| golf-root | valid | P | 119 | 0.486306 | 15.339867 | 15.826174 | 3684.931999 | 8.212007 |
| golf-probe | valid | P | 119 | 0.490293 | 16.779806 | 17.270099 | 4001.151653 | 8.294338 |
| golf-probe | valid | P | 119 | 0.481935 | 17.395302 | 17.877237 | 4134.114857 | 8.327029 |
| golf-root | valid | P | 119 | 0.506544 | 17.521008 | 18.027552 | 4167.033908 | 8.334960 |
| golf-blind | valid | P | 119 | 15.524493 | 11.992813 | 27.517306 | 6245.290107 | 8.739583 |
| golf-blind | valid | P | 119 | 14.909589 | 15.144349 | 30.053938 | 6800.812517 | 8.824797 |
| golf-blind | valid | P | 119 | 12.446855 | 17.849528 | 30.296383 | 6853.907897 | 8.832574 |
| interleaved | unsolved | unknown | — | 8.360984 | — | 8.360984 | — | — |
| interleaved | unsolved | unknown | — | 8.354794 | — | 8.354794 | — | — |
| interleaved | unsolved | unknown | — | 8.406094 | — | 8.406094 | — | — |

golf-blind: 3/3 valid; S min/median/max = 6245.290107/6800.812517/6853.907897; stdev = 337.105296.
golf-probe: 3/3 valid; S min/median/max = 3485.997160/4001.151653/4134.114857; stdev = 342.325361.
golf-root: 3/3 valid; S min/median/max = 3530.110683/3684.931999/4167.033908; stdev = 332.180444.
golf-witness: 3/3 valid; S min/median/max = 3355.097547/3510.981940/3523.040076; stdev = 93.675002.
interleaved: 0/3 valid.

## Target {16,26,62,89,98,102} — b2c5d97cc38ecefc

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | N | 193 | 0.502832 | 17.056698 | 17.559530 | 5437.942316 | 8.601156 |
| golf-root | valid | N | 103 | 0.394519 | 74.115101 | 74.509620 | 15328.452954 | 9.637466 |
| golf-probe | valid | N | 193 | 49.386834 | 15.805795 | 65.192629 | 19394.440217 | 9.872742 |
| golf-blind | valid | N | 103 | 71.700723 | 64.803441 | 136.504163 | 27913.345188 | 10.236860 |
| interleaved | unsolved | unknown | — | 8.288819 | — | 8.288819 | — | — |

golf-blind: 1/1 valid; S min/median/max = 27913.345188/27913.345188/27913.345188; stdev = 0.000000.
golf-probe: 1/1 valid; S min/median/max = 19394.440217/19394.440217/19394.440217; stdev = 0.000000.
golf-root: 1/1 valid; S min/median/max = 15328.452954/15328.452954/15328.452954; stdev = 0.000000.
golf-witness: 1/1 valid; S min/median/max = 5437.942316/5437.942316/5437.942316; stdev = 0.000000.
interleaved: 0/1 valid.

## Target {16,26,33,62,89,102} — d351420ed441cbee

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | P | 103 | 0.421241 | 13.485511 | 13.906752 | 3026.070713 | 8.015020 |
| golf-witness | valid | P | 103 | 0.455991 | 16.751389 | 17.207380 | 3696.098176 | 8.215033 |
| golf-probe | valid | P | 103 | 0.491282 | 18.982726 | 19.474008 | 4156.223707 | 8.332362 |
| golf-blind | valid | P | 103 | 18.310547 | 17.897503 | 36.208050 | 7553.234064 | 8.929731 |
| interleaved | unsolved | unknown | — | 7.763405 | — | 7.763405 | — | — |

golf-blind: 1/1 valid; S min/median/max = 7553.234064/7553.234064/7553.234064; stdev = 0.000000.
golf-probe: 1/1 valid; S min/median/max = 4156.223707/4156.223707/4156.223707; stdev = 0.000000.
golf-root: 1/1 valid; S min/median/max = 3026.070713/3026.070713/3026.070713; stdev = 0.000000.
golf-witness: 1/1 valid; S min/median/max = 3696.098176/3696.098176/3696.098176; stdev = 0.000000.
interleaved: 0/1 valid.

## Target {16,26,30,38,109,123,127,137} — e4f570c9badb3588

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | P | 121 | 0.475806 | 21.294336 | 21.770142 | 5032.201403 | 8.523613 |
| golf-root | valid | P | 121 | 0.497812 | 21.468735 | 21.966547 | 5075.606981 | 8.532201 |
| golf-root | valid | P | 121 | 0.478607 | 21.922431 | 22.401038 | 5171.629348 | 8.550943 |
| golf-probe | valid | P | 121 | 0.496387 | 22.121809 | 22.618196 | 5219.621384 | 8.560180 |
| golf-witness | valid | P | 121 | 0.506271 | 22.238175 | 22.744446 | 5247.522576 | 8.565511 |
| golf-probe | valid | P | 121 | 0.476728 | 22.452254 | 22.928982 | 5288.305122 | 8.573253 |
| golf-probe | valid | P | 121 | 0.504950 | 24.552770 | 25.057720 | 5758.756200 | 8.658477 |
| golf-root | valid | P | 121 | 0.495983 | 24.667016 | 25.162999 | 5782.022694 | 8.662509 |
| golf-witness | valid | P | 121 | 0.490926 | 25.251586 | 25.742512 | 5910.095179 | 8.684417 |
| golf-blind | valid | P | 121 | 16.760839 | 19.315566 | 36.076405 | 8193.885608 | 9.011143 |
| golf-blind | valid | P | 121 | 21.056484 | 17.209396 | 38.265880 | 8677.759521 | 9.068519 |
| golf-blind | valid | P | 121 | 24.967188 | 24.502043 | 49.469231 | 11153.700048 | 9.319527 |
| interleaved | unsolved | unknown | — | 7.792573 | — | 7.792573 | — | — |
| interleaved | unsolved | unknown | — | 8.062909 | — | 8.062909 | — | — |
| interleaved | unsolved | unknown | — | 8.029358 | — | 8.029358 | — | — |

golf-blind: 3/3 valid; S min/median/max = 8193.885608/8677.759521/11153.700048; stdev = 1587.708883.
golf-probe: 3/3 valid; S min/median/max = 5219.621384/5288.305122/5758.756200; stdev = 293.458692.
golf-root: 3/3 valid; S min/median/max = 5075.606981/5171.629348/5782.022694; stdev = 383.149991.
golf-witness: 3/3 valid; S min/median/max = 5032.201403/5247.522576/5910.095179; stdev = 457.541099.
interleaved: 0/3 valid.

## Target {16,26,82,86,88,93,129,149,163,169} — e89dccda8e818438

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | N | 217 | 0.509481 | 27.085660 | 27.595141 | 9064.659700 | 9.112139 |
| golf-root | valid | N | 133 | 0.355201 | 37.904123 | 38.259324 | 9147.422465 | 9.121227 |
| golf-witness | valid | N | 217 | 0.522754 | 32.787344 | 33.310098 | 10876.301035 | 9.294341 |
| golf-root | valid | N | 133 | 0.484751 | 46.136743 | 46.621493 | 11095.807958 | 9.314323 |
| golf-root | valid | N | 133 | 0.472225 | 46.231364 | 46.703589 | 11114.936269 | 9.316045 |
| golf-witness | valid | N | 217 | 0.471974 | 34.464284 | 34.936257 | 11391.793583 | 9.340649 |
| golf-blind | valid | N | 133 | 42.952892 | 37.331733 | 80.284625 | 18939.317607 | 9.848995 |
| golf-blind | valid | N | 133 | 42.869679 | 43.995353 | 86.865032 | 20472.552425 | 9.926840 |
| golf-blind | valid | N | 133 | 44.126799 | 45.022227 | 89.149026 | 21004.723173 | 9.952503 |
| golf-probe | valid | N | 217 | 58.249674 | 25.732299 | 83.981973 | 26939.285437 | 10.201341 |
| golf-probe | valid | N | 133 | 77.042595 | 46.738706 | 123.781301 | 29074.043082 | 10.277601 |
| golf-probe | valid | N | 217 | 79.948937 | 32.888744 | 112.837681 | 36086.544883 | 10.493675 |
| interleaved | unsolved | unknown | — | 8.167066 | — | 8.167066 | — | — |
| interleaved | unsolved | unknown | — | 8.273385 | — | 8.273385 | — | — |
| interleaved | unsolved | unknown | — | 8.070149 | — | 8.070149 | — | — |

golf-blind: 3/3 valid; S min/median/max = 18939.317607/20472.552425/21004.723173; stdev = 1072.373914.
golf-probe: 3/3 valid; S min/median/max = 26939.285437/29074.043082/36086.544883; stdev = 4785.476763.
golf-root: 3/3 valid; S min/median/max = 9147.422465/11095.807958/11114.936269; stdev = 1130.463215.
golf-witness: 3/3 valid; S min/median/max = 9064.659700/10876.301035/11391.793583; stdev = 1222.247179.
interleaved: 0/3 valid.

## Target {16,26,38,44,50,113,141,147,149,159} — f6e632b00ab6b0ec

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | P | 135 | 0.499595 | 47.859976 | 48.359570 | 11599.499017 | 9.358717 |
| golf-probe | valid | P | 135 | 0.494654 | 54.965864 | 55.460519 | 13268.221850 | 9.493127 |
| golf-root | valid | P | 135 | 0.480855 | 61.824939 | 62.305794 | 14876.861504 | 9.607562 |
| golf-witness | valid | P | 135 | 0.365337 | 62.089677 | 62.455015 | 14911.928462 | 9.609917 |
| golf-root | valid | P | 135 | 0.478562 | 63.047018 | 63.525579 | 15163.511104 | 9.626647 |
| golf-probe | valid | P | 135 | 0.481212 | 63.821214 | 64.302426 | 15346.070018 | 9.638615 |
| golf-witness | valid | P | 135 | 0.489288 | 66.291943 | 66.781231 | 15928.589294 | 9.675871 |
| golf-root | valid | P | 135 | 0.512943 | 66.900469 | 67.413411 | 16077.151648 | 9.685154 |
| golf-probe | valid | P | 135 | 0.372150 | 72.711449 | 73.083599 | 17409.645717 | 9.764780 |
| golf-blind | valid | P | 135 | 49.984440 | 55.097837 | 105.082278 | 24929.335226 | 10.123801 |
| golf-blind | valid | P | 135 | 55.664268 | 51.042456 | 106.706724 | 25311.080151 | 10.138998 |
| golf-blind | valid | P | 135 | 64.792936 | 59.791593 | 124.584528 | 29512.364170 | 10.292565 |
| interleaved | unsolved | unknown | — | 8.489150 | — | 8.489150 | — | — |
| interleaved | unsolved | unknown | — | 8.711722 | — | 8.711722 | — | — |
| interleaved | unsolved | unknown | — | 8.348794 | — | 8.348794 | — | — |

golf-blind: 3/3 valid; S min/median/max = 24929.335226/25311.080151/29512.364170; stdev = 2542.986135.
golf-probe: 3/3 valid; S min/median/max = 13268.221850/15346.070018/17409.645717; stdev = 2070.716032.
golf-root: 3/3 valid; S min/median/max = 14876.861504/15163.511104/16077.151648; stdev = 626.844408.
golf-witness: 3/3 valid; S min/median/max = 11599.499017/14911.928462/15928.589294; stdev = 2263.728882.
interleaved: 0/3 valid.

## Target {16,26,30,36,38,40,44,113,121,123,127,131} — ff5a29b89091d1c2

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | N | 147 | 0.499008 | 3.344404 | 3.843412 | 1196.322665 | 7.087008 |
| golf-root | valid | N | 147 | 0.511453 | 3.393727 | 3.905179 | 1211.579305 | 7.099680 |
| golf-root | valid | N | 147 | 0.499476 | 3.804204 | 4.303681 | 1310.009091 | 7.177789 |
| golf-witness | valid | N | 281 | 0.493018 | 2.164126 | 2.657143 | 1393.371673 | 7.239482 |
| golf-witness | valid | N | 281 | 0.512517 | 2.944693 | 3.457210 | 1698.196886 | 7.437322 |
| golf-witness | valid | N | 281 | 0.521984 | 3.015352 | 3.537336 | 1728.725097 | 7.455139 |
| golf-blind | valid | N | 147 | 3.636223 | 3.704054 | 7.340277 | 2060.048317 | 7.630485 |
| golf-blind | valid | N | 147 | 3.620774 | 3.813805 | 7.434579 | 2083.341020 | 7.641728 |
| golf-blind | valid | N | 147 | 3.786136 | 3.873216 | 7.659352 | 2138.859880 | 7.668028 |
| golf-probe | valid | N | 147 | 5.677730 | 2.713578 | 8.391308 | 2319.653000 | 7.749173 |
| golf-probe | valid | N | 147 | 5.094580 | 3.653796 | 8.748376 | 2407.848908 | 7.786489 |
| golf-probe | valid | N | 147 | 7.039209 | 3.820882 | 10.860091 | 2929.442512 | 7.982567 |
| interleaved | unsolved | unknown | — | 7.643804 | — | 7.643804 | — | — |
| interleaved | unsolved | unknown | — | 8.095602 | — | 8.095602 | — | — |
| interleaved | unsolved | unknown | — | 7.950759 | — | 7.950759 | — | — |

golf-blind: 3/3 valid; S min/median/max = 2060.048317/2083.341020/2138.859880; stdev = 40.489003.
golf-probe: 3/3 valid; S min/median/max = 2319.653000/2407.848908/2929.442512; stdev = 329.565789.
golf-root: 3/3 valid; S min/median/max = 1196.322665/1211.579305/1310.009091; stdev = 61.706012.
golf-witness: 3/3 valid; S min/median/max = 1393.371673/1698.196886/1728.725097; stdev = 185.432963.
interleaved: 0/3 valid.

## Coverage (separate from per-target scores)

- golf-blind: 14/16 distinct tasks solved.
- golf-probe: 16/16 distinct tasks solved.
- golf-root: 16/16 distinct tasks solved.
- golf-witness: 16/16 distinct tasks solved.
- interleaved: 0/16 distinct tasks solved.

