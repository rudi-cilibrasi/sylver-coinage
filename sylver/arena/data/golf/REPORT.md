# Certificate golf pilot

Every target is a public database result, so golf measures how cheaply a program can
*certify* a known outcome, not discovery. Hints are untrusted: every certificate here was
replayed by the fixed verifier with a fresh memo. S=(C+100)*(T+1), lower is better;
T is discovery plus verification CPU seconds. No new mathematics is claimed.

## Median S per target

| Target | Tier | Outcome | golf-probe | golf-root | golf-witness | increasing | interleaved |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `{16,20,26,28,38,111,121,129,135}` | A | P | 669 | 601 | 678 | — | — |
| `{16,26,28,30,38,79}` | A | P | 1164 | 992 | 1127 | — | — |
| `{16,26,30,36,38,40,44,113,121,123,127,131}` | A | N | 2568 | 1155 | 1604 | — | — |
| `{16,26,30,36,38,50,115,125,139,159}` | A | N | 381 | 368 | 461 | — | — |
| `{16,26,30,38,109,123,127,137}` | A | P | 4619 | 4527 | 4932 | — | — |
| `{16,26,34,38,40,117,123,125,127,131}` | A | N | 4457 | 1942 | 2124 | — | — |
| `{16,26,34,38,40,115,151,159}` | B | P | 3473 | 2908 | 2973 | — | — |
| `{16,26,36,38,44,56,66,119,137,139,141,147}` | B | N | 19836 | 7153 | 11218 | — | — |
| `{16,26,38,44,46,56,111,129,131,133}` | B | P | 9012 | 9226 | 8745 | — | — |
| `{16,26,38,44,50,113,141,147,149,159}` | B | P | 15453 | 13845 | 15162 | — | — |
| `{16,26,70,82,83,88,133,137}` | B | N | 8302 | 3527 | 2658 | — | — |
| `{16,26,82,86,88,93,129,149,163,169}` | B | N | 27558 | 10001 | 9656 | — | — |
| `{16,26,33,62,89,102}` | C | P | 3978 | 4015 | 3948 | — | — |
| `{16,26,62,89,98,102}` | C | N | 19039 | 17434 | 5922 | — | — |
| `{16,26,62,98,102}` | C | N | 253529 | 220168 | 214474 | — | — |
| `{16,26,62,98,134}` | C | N | 202225 | 163365 | 159389 | — | — |

## Lowest median S by target

- golf-probe: 0 of 16 targets
- golf-root: 9 of 16 targets
- golf-witness: 7 of 16 targets
- increasing: 0 of 16 targets
- interleaved: 0 of 16 targets

## Findings and decision

Three repetitions of tiers A and B and one of tier C, 200 episodes, all
under one execution profile on a shared, heavily loaded workstation. CPU
times ran about twice the historical replay of the same W134 certificate
(554 s against 266 s), so compare scores only within this run.

1. **Hints matter more than strategy.** The two pre-existing search
   baselines certified nothing: their fixed 0.3–0.6 s query slices cannot
   solve positions whose root search takes 1–60 s, and without hints they
   have no cheaper route. Every golf strategy certified every target.
2. **Structure matters, but only when the database offers a much cheaper
   witness.** On the seven finite N targets, a witness edge costs about
   twice the bytes of a root leaf, which is a factor of about 1.5 in
   `(C+100)`. The root leaf had the lower median S on four targets; the
   witness won on three, by 1.04×, 1.33× and **2.94×**. The 2.94× case is
   `{16,26,62,89,98,102}`, where the verifier's own root search takes
   6,382,154 states against 1,721,485 for the hinted witness 33.
3. **P targets and gcd-two targets offer no choice.** Every strategy
   submitted the same certificate, so their different "winners" are timing
   noise, visible in the per-run tables.
4. **Probing does not pay.** `golf-probe` measures candidates by solving
   them, which costs about as much as verifying them. It had the highest
   median S on 11 of 16 targets and never the lowest.

**Decision: continue, with cost prediction as the next step.** Golf
separates good certificates from bad ones by up to 2.9× on real campaign
positions, and the Book now records deterministic state counts for every
admitted certificate. The next competitor to build is a cost-aware golfer
that predicts verification cost cheaply, for example from recorded Book
state counts or structural proxies such as Frobenius number and genus,
instead of measuring by solving. External programs and model-driven agents
can compete through the same protocol and pinned hints.

The Book seeded by this pilot is [sylver/arena/book/BOOK.md](../../book/BOOK.md); per-run leaderboards follow.

# Golf leaderboards

Scores are compared only within an identical target, snapshot, verifier, and execution profile.

C is canonical UTF-8 proof bytes; T is discovery + verification CPU seconds. Lower S=(C+100)*(T+1) is better.

## Target {16,26,70,82,83,88,133,137} — 08e780b431f8af88

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | N | 205 | 0.418416 | 6.377859 | 6.796275 | 2377.863905 | 7.773958 |
| golf-witness | valid | N | 205 | 0.459210 | 7.255248 | 7.714459 | 2657.909878 | 7.885295 |
| golf-witness | valid | N | 205 | 0.463258 | 8.502104 | 8.965361 | 3039.435222 | 8.019427 |
| golf-root | valid | N | 117 | 0.447509 | 13.961489 | 14.408998 | 3343.752543 | 8.114849 |
| golf-root | valid | N | 117 | 0.435327 | 14.820338 | 15.255665 | 3527.479265 | 8.168339 |
| golf-root | valid | N | 117 | 0.433606 | 14.962787 | 15.396393 | 3558.017256 | 8.176959 |
| golf-probe | valid | N | 205 | 14.177507 | 8.147708 | 22.325215 | 7114.190603 | 8.869847 |
| golf-probe | valid | N | 205 | 20.321172 | 5.899988 | 26.221160 | 8302.453829 | 9.024306 |
| golf-probe | valid | N | 205 | 19.978991 | 8.684899 | 28.663891 | 9047.486645 | 9.110242 |
| interleaved | unsolved | unknown | — | 7.628281 | — | 7.628281 | — | — |
| increasing | unsolved | unknown | — | 2.235677 | — | 2.235677 | — | — |
| interleaved | unsolved | unknown | — | 8.026454 | — | 8.026454 | — | — |
| increasing | unsolved | unknown | — | 1.969640 | — | 1.969640 | — | — |
| interleaved | unsolved | unknown | — | 8.226735 | — | 8.226735 | — | — |
| increasing | unsolved | unknown | — | 2.273829 | — | 2.273829 | — | — |

golf-probe: 3/3 valid; S min/median/max = 7114.190603/8302.453829/9047.486645; stdev = 975.079225.
golf-root: 3/3 valid; S min/median/max = 3343.752543/3527.479265/3558.017256; stdev = 115.900420.
golf-witness: 3/3 valid; S min/median/max = 2377.863905/2657.909878/3039.435222; stdev = 332.080297.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Target {16,26,82,86,88,93,129,149,163,169} — 1002c988b71d1957

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | N | 133 | 0.388487 | 34.140906 | 34.529393 | 8278.348548 | 9.021399 |
| golf-witness | valid | N | 217 | 0.491618 | 26.183357 | 26.674975 | 8772.967097 | 9.079430 |
| golf-witness | valid | N | 217 | 0.530951 | 28.928606 | 29.459557 | 9655.679604 | 9.175302 |
| golf-root | valid | N | 133 | 0.577692 | 41.346570 | 41.924262 | 10001.353032 | 9.210476 |
| golf-root | valid | N | 133 | 0.456309 | 45.326832 | 45.783141 | 10900.471917 | 9.296561 |
| golf-witness | valid | N | 217 | 0.502390 | 33.159956 | 33.662346 | 10987.963761 | 9.304556 |
| golf-probe | valid | N | 133 | 66.110343 | 39.316809 | 105.427152 | 24797.526393 | 10.118499 |
| golf-probe | valid | N | 217 | 60.008159 | 25.925180 | 85.933338 | 27557.868247 | 10.224043 |
| golf-probe | valid | N | 217 | 78.465448 | 33.700098 | 112.165546 | 35873.478165 | 10.487754 |
| interleaved | unsolved | unknown | — | 7.887589 | — | 7.887589 | — | — |
| increasing | unsolved | unknown | — | 2.666738 | — | 2.666738 | — | — |
| interleaved | unsolved | unknown | — | 7.897926 | — | 7.897926 | — | — |
| increasing | unsolved | unknown | — | 2.450967 | — | 2.450967 | — | — |
| interleaved | unsolved | unknown | — | 8.299275 | — | 8.299275 | — | — |
| increasing | unsolved | unknown | — | 2.638281 | — | 2.638281 | — | — |

golf-probe: 3/3 valid; S min/median/max = 24797.526393/27557.868247/35873.478165; stdev = 5765.494531.
golf-root: 3/3 valid; S min/median/max = 8278.348548/10001.353032/10900.471917; stdev = 1332.459517.
golf-witness: 3/3 valid; S min/median/max = 8772.967097/9655.679604/10987.963761; stdev = 1115.076430.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Target {16,26,30,36,38,50,115,125,139,159} — 2c627e8566332a47

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | N | 133 | 0.394531 | 0.137600 | 0.532131 | 356.986550 | 5.877698 |
| golf-root | valid | N | 133 | 0.419382 | 0.161547 | 0.580929 | 368.356491 | 5.909051 |
| golf-probe | valid | N | 133 | 0.420670 | 0.189003 | 0.609673 | 375.053735 | 5.927069 |
| golf-probe | valid | N | 133 | 0.474602 | 0.161103 | 0.635704 | 381.119090 | 5.943112 |
| golf-root | valid | N | 133 | 0.472907 | 0.173983 | 0.646890 | 383.725438 | 5.949927 |
| golf-probe | valid | N | 133 | 0.495747 | 0.178677 | 0.674424 | 390.140811 | 5.966508 |
| golf-witness | valid | N | 210 | 0.306765 | 0.168999 | 0.475765 | 457.487098 | 6.125749 |
| golf-witness | valid | N | 210 | 0.339197 | 0.147769 | 0.486966 | 460.959402 | 6.133310 |
| golf-witness | valid | N | 210 | 0.498905 | 0.177270 | 0.676175 | 519.614403 | 6.253087 |
| interleaved | unsolved | unknown | — | 7.918321 | — | 7.918321 | — | — |
| increasing | unsolved | unknown | — | 2.023316 | — | 2.023316 | — | — |
| interleaved | unsolved | unknown | — | 7.955960 | — | 7.955960 | — | — |
| increasing | unsolved | unknown | — | 1.736121 | — | 1.736121 | — | — |
| interleaved | unsolved | unknown | — | 7.890865 | — | 7.890865 | — | — |
| increasing | unsolved | unknown | — | 1.731821 | — | 1.731821 | — | — |

golf-probe: 3/3 valid; S min/median/max = 375.053735/381.119090/390.140811; stdev = 7.591661.
golf-root: 3/3 valid; S min/median/max = 356.986550/368.356491/383.725438; stdev = 13.419191.
golf-witness: 3/3 valid; S min/median/max = 457.487098/460.959402/519.614403; stdev = 34.910046.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Target {16,26,62,89,98,102} — 34b3730ee7537231

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | N | 193 | 0.521708 | 18.690776 | 19.212484 | 5922.257873 | 8.686473 |
| golf-root | valid | N | 103 | 0.421371 | 84.461103 | 84.882473 | 17434.142115 | 9.766186 |
| golf-probe | valid | N | 193 | 45.183942 | 18.794106 | 63.978048 | 19038.568023 | 9.854222 |
| interleaved | unsolved | unknown | — | 8.101765 | — | 8.101765 | — | — |
| increasing | unsolved | unknown | — | 2.562528 | — | 2.562528 | — | — |

golf-probe: 1/1 valid; S min/median/max = 19038.568023/19038.568023/19038.568023; stdev = 0.000000.
golf-root: 1/1 valid; S min/median/max = 17434.142115/17434.142115/17434.142115; stdev = 0.000000.
golf-witness: 1/1 valid; S min/median/max = 5922.257873/5922.257873/5922.257873; stdev = 0.000000.
increasing: 0/1 valid.
interleaved: 0/1 valid.

## Target {16,26,62,98,134} — 44dd7a97c6e8bf08

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | N | 187 | 0.458540 | 553.904146 | 554.362686 | 159389.090970 | 11.979104 |
| golf-root | valid | N | 187 | 0.443819 | 567.770953 | 568.214772 | 163364.639470 | 12.003740 |
| golf-probe | valid | N | 187 | 127.532737 | 576.083775 | 703.616512 | 202224.938997 | 12.217136 |
| interleaved | unsolved | unknown | — | 7.603932 | — | 7.603932 | — | — |
| increasing | unsolved | unknown | — | 2.158161 | — | 2.158161 | — | — |

golf-probe: 1/1 valid; S min/median/max = 202224.938997/202224.938997/202224.938997; stdev = 0.000000.
golf-root: 1/1 valid; S min/median/max = 163364.639470/163364.639470/163364.639470; stdev = 0.000000.
golf-witness: 1/1 valid; S min/median/max = 159389.090970/159389.090970/159389.090970; stdev = 0.000000.
increasing: 0/1 valid.
interleaved: 0/1 valid.

## Target {16,26,33,62,89,102} — 48bea8c804a76242

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | P | 103 | 0.462269 | 17.986860 | 18.449129 | 3948.173174 | 8.281008 |
| golf-probe | valid | P | 103 | 0.509245 | 18.085743 | 18.594988 | 3977.782463 | 8.288480 |
| golf-root | valid | P | 103 | 0.487439 | 18.291966 | 18.779405 | 4015.219203 | 8.297847 |
| interleaved | unsolved | unknown | — | 7.569203 | — | 7.569203 | — | — |
| increasing | unsolved | unknown | — | 2.108753 | — | 2.108753 | — | — |

golf-probe: 1/1 valid; S min/median/max = 3977.782463/3977.782463/3977.782463; stdev = 0.000000.
golf-root: 1/1 valid; S min/median/max = 4015.219203/4015.219203/4015.219203; stdev = 0.000000.
golf-witness: 1/1 valid; S min/median/max = 3948.173174/3948.173174/3948.173174; stdev = 0.000000.
increasing: 0/1 valid.
interleaved: 0/1 valid.

## Target {16,26,30,38,109,123,127,137} — 4f376e23ec0e7467

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | P | 121 | 0.404327 | 15.978626 | 16.382953 | 3841.632532 | 8.253653 |
| golf-probe | valid | P | 121 | 0.418676 | 17.619188 | 18.037863 | 4207.367788 | 8.344593 |
| golf-root | valid | P | 121 | 0.428505 | 19.054422 | 19.482926 | 4526.726746 | 8.417754 |
| golf-witness | valid | P | 121 | 0.330187 | 19.345861 | 19.676048 | 4569.406509 | 8.427139 |
| golf-probe | valid | P | 121 | 0.403412 | 19.498371 | 19.901783 | 4619.294044 | 8.437997 |
| golf-witness | valid | P | 121 | 0.445222 | 20.873498 | 21.318720 | 4932.437033 | 8.503588 |
| golf-root | valid | P | 121 | 0.437290 | 22.338124 | 22.775414 | 5254.366564 | 8.566815 |
| golf-witness | valid | P | 121 | 0.465435 | 22.708961 | 23.174397 | 5342.541642 | 8.583457 |
| golf-probe | valid | P | 121 | 0.417890 | 22.764787 | 23.182677 | 5344.371533 | 8.583799 |
| interleaved | unsolved | unknown | — | 7.796673 | — | 7.796673 | — | — |
| increasing | unsolved | unknown | — | 2.059990 | — | 2.059990 | — | — |
| interleaved | unsolved | unknown | — | 7.909197 | — | 7.909197 | — | — |
| increasing | unsolved | unknown | — | 2.031534 | — | 2.031534 | — | — |
| interleaved | unsolved | unknown | — | 7.852906 | — | 7.852906 | — | — |
| increasing | unsolved | unknown | — | 1.913785 | — | 1.913785 | — | — |

golf-probe: 3/3 valid; S min/median/max = 4207.367788/4619.294044/5344.371533; stdev = 575.644295.
golf-root: 3/3 valid; S min/median/max = 3841.632532/4526.726746/5254.366564; stdev = 706.473783.
golf-witness: 3/3 valid; S min/median/max = 4569.406509/4932.437033/5342.541642; stdev = 386.806344.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Target {16,26,34,38,40,115,151,159} — 58c58369ce609322

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | P | 119 | 0.316390 | 10.914313 | 11.230704 | 2678.524103 | 7.893021 |
| golf-probe | valid | P | 119 | 0.302042 | 11.869952 | 12.171994 | 2884.666681 | 7.967165 |
| golf-root | valid | P | 119 | 0.412286 | 11.867216 | 12.279501 | 2908.210825 | 7.975293 |
| golf-witness | valid | P | 119 | 0.421688 | 12.088447 | 12.510136 | 2958.719675 | 7.992512 |
| golf-witness | valid | P | 119 | 0.507262 | 12.069505 | 12.576766 | 2973.311842 | 7.997432 |
| golf-probe | valid | P | 119 | 0.431171 | 14.425503 | 14.856674 | 3472.611654 | 8.152662 |
| golf-root | valid | P | 119 | 0.460215 | 16.717384 | 17.177599 | 3980.894215 | 8.289262 |
| golf-probe | valid | P | 119 | 0.459587 | 16.779672 | 17.239259 | 3994.397710 | 8.292648 |
| golf-witness | valid | P | 119 | 0.480404 | 16.810582 | 17.290986 | 4005.725860 | 8.295480 |
| interleaved | unsolved | unknown | — | 8.013046 | — | 8.013046 | — | — |
| increasing | unsolved | unknown | — | 2.259846 | — | 2.259846 | — | — |
| interleaved | unsolved | unknown | — | 8.190225 | — | 8.190225 | — | — |
| increasing | unsolved | unknown | — | 2.045310 | — | 2.045310 | — | — |
| interleaved | unsolved | unknown | — | 8.234308 | — | 8.234308 | — | — |
| increasing | unsolved | unknown | — | 1.951265 | — | 1.951265 | — | — |

golf-probe: 3/3 valid; S min/median/max = 2884.666681/3472.611654/3994.397710; stdev = 555.194101.
golf-root: 3/3 valid; S min/median/max = 2678.524103/2908.210825/3980.894215; stdev = 695.170669.
golf-witness: 3/3 valid; S min/median/max = 2958.719675/2973.311842/4005.725860; stdev = 600.321246.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Target {16,26,38,44,50,113,141,147,149,159} — 882ceec1a6f9e006

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-probe | valid | P | 135 | 0.447430 | 48.988780 | 49.436210 | 11852.509352 | 9.380295 |
| golf-witness | valid | P | 135 | 0.410600 | 55.172207 | 55.582807 | 13296.959692 | 9.495291 |
| golf-root | valid | P | 135 | 0.432507 | 56.183358 | 56.615864 | 13539.728142 | 9.513383 |
| golf-root | valid | P | 135 | 0.391173 | 57.521686 | 57.912859 | 13844.521779 | 9.535645 |
| golf-witness | valid | P | 135 | 0.470486 | 63.049705 | 63.520191 | 15162.244903 | 9.626564 |
| golf-root | valid | P | 135 | 0.496023 | 63.427476 | 63.923499 | 15257.022235 | 9.632795 |
| golf-probe | valid | P | 135 | 0.481317 | 64.275496 | 64.756814 | 15452.851270 | 9.645549 |
| golf-probe | valid | P | 135 | 0.400710 | 66.259622 | 66.660332 | 15900.178026 | 9.674086 |
| golf-witness | valid | P | 135 | 0.437425 | 68.664767 | 69.102192 | 16474.015167 | 9.709540 |
| interleaved | unsolved | unknown | — | 8.670520 | — | 8.670520 | — | — |
| increasing | unsolved | unknown | — | 2.472498 | — | 2.472498 | — | — |
| interleaved | unsolved | unknown | — | 8.376961 | — | 8.376961 | — | — |
| increasing | unsolved | unknown | — | 2.452124 | — | 2.452124 | — | — |
| interleaved | unsolved | unknown | — | 8.482546 | — | 8.482546 | — | — |
| increasing | unsolved | unknown | — | 2.246977 | — | 2.246977 | — | — |

golf-probe: 3/3 valid; S min/median/max = 11852.509352/15452.851270/15900.178026; stdev = 2219.090837.
golf-root: 3/3 valid; S min/median/max = 13539.728142/13844.521779/15257.022235; stdev = 916.256487.
golf-witness: 3/3 valid; S min/median/max = 13296.959692/15162.244903/16474.015167; stdev = 1596.543748.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Target {16,26,30,36,38,40,44,113,121,123,127,131} — 972e08c772b31663

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | N | 147 | 0.431574 | 3.133349 | 3.564923 | 1127.535929 | 7.027790 |
| golf-root | valid | N | 147 | 0.461628 | 3.214287 | 3.675915 | 1154.951102 | 7.051813 |
| golf-root | valid | N | 147 | 0.472069 | 3.419922 | 3.891991 | 1208.321740 | 7.096988 |
| golf-witness | valid | N | 281 | 0.419271 | 1.841232 | 2.260503 | 1242.251787 | 7.124681 |
| golf-witness | valid | N | 281 | 0.413605 | 2.797622 | 3.211227 | 1604.477332 | 7.380553 |
| golf-witness | valid | N | 281 | 0.488434 | 2.821525 | 3.309959 | 1642.094222 | 7.403728 |
| golf-probe | valid | N | 147 | 4.345530 | 2.981820 | 7.327350 | 2056.855453 | 7.628934 |
| golf-probe | valid | N | 147 | 6.106695 | 3.289901 | 9.396596 | 2567.959196 | 7.850867 |
| golf-probe | valid | N | 147 | 6.263661 | 3.217753 | 9.481413 | 2588.909130 | 7.858992 |
| interleaved | unsolved | unknown | — | 7.813029 | — | 7.813029 | — | — |
| increasing | unsolved | unknown | — | 1.692490 | — | 1.692490 | — | — |
| interleaved | unsolved | unknown | — | 7.939721 | — | 7.939721 | — | — |
| increasing | unsolved | unknown | — | 1.525072 | — | 1.525072 | — | — |
| interleaved | unsolved | unknown | — | 7.886439 | — | 7.886439 | — | — |
| increasing | unsolved | unknown | — | 1.466573 | — | 1.466573 | — | — |

golf-probe: 3/3 valid; S min/median/max = 2056.855453/2567.959196/2588.909130; stdev = 301.315740.
golf-root: 3/3 valid; S min/median/max = 1127.535929/1154.951102/1208.321740; stdev = 41.081958.
golf-witness: 3/3 valid; S min/median/max = 1242.251787/1604.477332/1642.094222; stdev = 220.792644.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Target {16,26,34,38,40,117,123,125,127,131} — a0704b3756801d44

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | N | 135 | 0.397465 | 4.906188 | 5.303653 | 1481.358513 | 7.300715 |
| golf-root | valid | N | 135 | 0.438103 | 6.824325 | 7.262428 | 1941.670584 | 7.571304 |
| golf-root | valid | N | 135 | 0.453450 | 7.128057 | 7.581506 | 2016.653965 | 7.609195 |
| golf-witness | valid | N | 263 | 0.476260 | 4.309672 | 4.785933 | 2100.293513 | 7.649832 |
| golf-witness | valid | N | 263 | 0.484985 | 4.365459 | 4.850444 | 2123.711332 | 7.660920 |
| golf-witness | valid | N | 263 | 0.469241 | 4.385144 | 4.854385 | 2125.141837 | 7.661594 |
| golf-probe | valid | N | 135 | 11.028460 | 6.475046 | 17.503505 | 4348.323759 | 8.377546 |
| golf-probe | valid | N | 135 | 11.551066 | 6.415910 | 17.966976 | 4457.239253 | 8.402285 |
| golf-probe | valid | N | 135 | 11.423646 | 6.548589 | 17.972236 | 4458.475351 | 8.402562 |
| interleaved | unsolved | unknown | — | 8.081926 | — | 8.081926 | — | — |
| increasing | unsolved | unknown | — | 1.986634 | — | 1.986634 | — | — |
| interleaved | unsolved | unknown | — | 8.098542 | — | 8.098542 | — | — |
| increasing | unsolved | unknown | — | 1.909500 | — | 1.909500 | — | — |
| interleaved | unsolved | unknown | — | 8.119190 | — | 8.119190 | — | — |
| increasing | unsolved | unknown | — | 1.743785 | — | 1.743785 | — | — |

golf-probe: 3/3 valid; S min/median/max = 4348.323759/4457.239253/4458.475351; stdev = 63.242241.
golf-root: 3/3 valid; S min/median/max = 1481.358513/1941.670584/2016.653965; stdev = 289.842179.
golf-witness: 3/3 valid; S min/median/max = 2100.293513/2123.711332/2125.141837; stdev = 13.951581.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Target {16,26,62,98,102} — a25db321fe0c6ba7

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-witness | valid | N | 187 | 0.568431 | 745.726005 | 746.294436 | 214473.503087 | 12.275941 |
| golf-root | valid | N | 187 | 0.514674 | 765.620686 | 766.135361 | 220167.848509 | 12.302145 |
| golf-probe | valid | N | 187 | 122.694440 | 759.681722 | 882.376162 | 253528.958505 | 12.443233 |
| interleaved | unsolved | unknown | — | 7.732252 | — | 7.732252 | — | — |
| increasing | unsolved | unknown | — | 2.058801 | — | 2.058801 | — | — |

golf-probe: 1/1 valid; S min/median/max = 253528.958505/253528.958505/253528.958505; stdev = 0.000000.
golf-root: 1/1 valid; S min/median/max = 220167.848509/220167.848509/220167.848509; stdev = 0.000000.
golf-witness: 1/1 valid; S min/median/max = 214473.503087/214473.503087/214473.503087; stdev = 0.000000.
increasing: 0/1 valid.
interleaved: 0/1 valid.

## Target {16,20,26,28,38,111,121,129,135} — c21da2cf38c787f1

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | P | 127 | 0.405967 | 1.209322 | 1.615289 | 593.670491 | 6.386324 |
| golf-probe | valid | P | 127 | 0.450913 | 1.178402 | 1.629315 | 596.854400 | 6.391673 |
| golf-root | valid | P | 127 | 0.408889 | 1.236836 | 1.645725 | 600.579542 | 6.397895 |
| golf-root | valid | P | 127 | 0.431463 | 1.505453 | 1.936916 | 666.679960 | 6.502310 |
| golf-probe | valid | P | 127 | 0.436884 | 1.511544 | 1.948428 | 669.293252 | 6.506222 |
| golf-witness | valid | P | 127 | 0.458332 | 1.513816 | 1.972148 | 674.677505 | 6.514235 |
| golf-witness | valid | P | 127 | 0.459255 | 1.527558 | 1.986813 | 678.006614 | 6.519157 |
| golf-probe | valid | P | 127 | 0.418561 | 1.576726 | 1.995287 | 679.930227 | 6.521990 |
| golf-witness | valid | P | 127 | 0.396874 | 1.814037 | 2.210910 | 728.876656 | 6.591505 |
| interleaved | unsolved | unknown | — | 7.099935 | — | 7.099935 | — | — |
| increasing | unsolved | unknown | — | 1.201260 | — | 1.201260 | — | — |
| interleaved | unsolved | unknown | — | 7.398802 | — | 7.398802 | — | — |
| increasing | unsolved | unknown | — | 1.229640 | — | 1.229640 | — | — |
| interleaved | unsolved | unknown | — | 7.167559 | — | 7.167559 | — | — |
| increasing | unsolved | unknown | — | 1.076058 | — | 1.076058 | — | — |

golf-probe: 3/3 valid; S min/median/max = 596.854400/669.293252/679.930227; stdev = 45.207163.
golf-root: 3/3 valid; S min/median/max = 593.670491/600.579542/666.679960; stdev = 40.305878.
golf-witness: 3/3 valid; S min/median/max = 674.677505/678.006614/728.876656; stdev = 30.376504.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Target {16,26,36,38,44,56,66,119,137,139,141,147} — c95fe9bf74148495

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | N | 147 | 0.403346 | 21.828327 | 22.231673 | 5738.223140 | 8.654905 |
| golf-root | valid | N | 147 | 0.442311 | 27.517962 | 27.960273 | 7153.187433 | 8.875313 |
| golf-root | valid | N | 147 | 0.430164 | 28.297813 | 28.727977 | 7342.810436 | 8.901477 |
| golf-witness | valid | N | 282 | 0.437856 | 27.060009 | 27.497865 | 10886.184283 | 9.295250 |
| golf-witness | valid | N | 282 | 0.529117 | 27.836286 | 28.365403 | 11217.584006 | 9.325238 |
| golf-witness | valid | N | 282 | 0.507957 | 29.014792 | 29.522749 | 11659.690248 | 9.363893 |
| golf-probe | valid | N | 147 | 53.594171 | 22.661002 | 76.255173 | 19082.027713 | 9.856502 |
| golf-probe | valid | N | 147 | 55.453640 | 23.854636 | 79.308276 | 19836.144159 | 9.895261 |
| golf-probe | valid | N | 147 | 58.995391 | 28.925167 | 87.920559 | 21963.377960 | 9.997132 |
| interleaved | unsolved | unknown | — | 7.728409 | — | 7.728409 | — | — |
| increasing | unsolved | unknown | — | 2.314969 | — | 2.314969 | — | — |
| interleaved | unsolved | unknown | — | 8.022006 | — | 8.022006 | — | — |
| increasing | unsolved | unknown | — | 2.018243 | — | 2.018243 | — | — |
| interleaved | unsolved | unknown | — | 8.170544 | — | 8.170544 | — | — |
| increasing | unsolved | unknown | — | 2.491142 | — | 2.491142 | — | — |

golf-probe: 3/3 valid; S min/median/max = 19082.027713/19836.144159/21963.377960; stdev = 1494.210745.
golf-root: 3/3 valid; S min/median/max = 5738.223140/7153.187433/7342.810436; stdev = 876.810624.
golf-witness: 3/3 valid; S min/median/max = 10886.184283/11217.584006/11659.690248; stdev = 388.071124.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Target {16,26,28,30,38,79} — d03512677eda6e4f

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-probe | valid | P | 101 | 0.314637 | 2.990111 | 3.304748 | 865.254418 | 6.763024 |
| golf-root | valid | P | 101 | 0.331557 | 3.248760 | 3.580317 | 920.643700 | 6.825073 |
| golf-root | valid | P | 101 | 0.418425 | 3.516666 | 3.935091 | 991.953225 | 6.899676 |
| golf-witness | valid | P | 101 | 0.421687 | 3.699841 | 4.121528 | 1029.427195 | 6.936758 |
| golf-witness | valid | P | 101 | 0.425466 | 4.183475 | 4.608941 | 1127.397070 | 7.027667 |
| golf-root | valid | P | 101 | 0.446834 | 4.234138 | 4.680972 | 1141.875391 | 7.040427 |
| golf-witness | valid | P | 101 | 0.456536 | 4.308613 | 4.765149 | 1158.795020 | 7.055136 |
| golf-probe | valid | P | 101 | 0.415349 | 4.373902 | 4.789251 | 1163.639388 | 7.059308 |
| golf-probe | valid | P | 101 | 0.477336 | 4.700961 | 5.178297 | 1241.837774 | 7.124348 |
| interleaved | unsolved | unknown | — | 7.474599 | — | 7.474599 | — | — |
| increasing | unsolved | unknown | — | 1.171788 | — | 1.171788 | — | — |
| interleaved | unsolved | unknown | — | 7.531001 | — | 7.531001 | — | — |
| increasing | unsolved | unknown | — | 1.098165 | — | 1.098165 | — | — |
| interleaved | unsolved | unknown | — | 7.483151 | — | 7.483151 | — | — |
| increasing | unsolved | unknown | — | 1.010610 | — | 1.010610 | — | — |

golf-probe: 3/3 valid; S min/median/max = 865.254418/1163.639388/1241.837774; stdev = 198.730807.
golf-root: 3/3 valid; S min/median/max = 920.643700/991.953225/1141.875391; stdev = 112.919710.
golf-witness: 3/3 valid; S min/median/max = 1029.427195/1127.397070/1158.795020; stdev = 67.478345.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Target {16,26,38,44,46,56,111,129,131,133} — dc0b1941af1e15f3

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| golf-root | valid | P | 133 | 0.317646 | 31.013126 | 31.330772 | 7533.069920 | 8.927058 |
| golf-probe | valid | P | 133 | 0.386458 | 34.380991 | 34.767449 | 8333.815566 | 9.028077 |
| golf-witness | valid | P | 133 | 0.413914 | 35.303743 | 35.717657 | 8555.214006 | 9.054296 |
| golf-witness | valid | P | 133 | 0.459743 | 36.074137 | 36.533879 | 8745.393868 | 9.076282 |
| golf-probe | valid | P | 133 | 0.401376 | 37.277703 | 37.679079 | 9012.225491 | 9.106337 |
| golf-root | valid | P | 133 | 0.386104 | 38.211380 | 38.597485 | 9226.213956 | 9.129804 |
| golf-root | valid | P | 133 | 0.480125 | 42.233763 | 42.713888 | 10185.336005 | 9.228704 |
| golf-probe | valid | P | 133 | 0.504755 | 42.419132 | 42.923887 | 10234.265608 | 9.233497 |
| golf-witness | valid | P | 133 | 0.460741 | 42.660129 | 43.120870 | 10280.162668 | 9.237971 |
| interleaved | unsolved | unknown | — | 7.829169 | — | 7.829169 | — | — |
| increasing | unsolved | unknown | — | 1.833580 | — | 1.833580 | — | — |
| interleaved | unsolved | unknown | — | 8.005581 | — | 8.005581 | — | — |
| increasing | unsolved | unknown | — | 1.324549 | — | 1.324549 | — | — |
| interleaved | unsolved | unknown | — | 8.032745 | — | 8.032745 | — | — |
| increasing | unsolved | unknown | — | 1.625141 | — | 1.625141 | — | — |

golf-probe: 3/3 valid; S min/median/max = 8333.815566/9012.225491/10234.265608; stdev = 963.096779.
golf-root: 3/3 valid; S min/median/max = 7533.069920/9226.213956/10185.336005; stdev = 1342.954903.
golf-witness: 3/3 valid; S min/median/max = 8555.214006/8745.393868/10280.162668; stdev = 945.791691.
increasing: 0/3 valid.
interleaved: 0/3 valid.

## Coverage (separate from per-target scores)

- golf-probe: 16/16 distinct tasks solved.
- golf-root: 16/16 distinct tasks solved.
- golf-witness: 16/16 distinct tasks solved.
- increasing: 0/16 distinct tasks solved.
- interleaved: 0/16 distinct tasks solved.

