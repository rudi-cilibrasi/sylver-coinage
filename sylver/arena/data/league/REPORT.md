# Game arena league

**Game results are not proofs.** A win, a rating, or a win rate here is evidence about these programs under these clocks, never about the outcome of a position. Openings are *capped* unless they have gcd one and a Frobenius number at most the move cap 1000; the empty position is capped. Capped games follow a house rule: moves are limited to 2..1000, which never ends a game early but removes larger moves, so their games say nothing about real Sylver Coinage. Only uncapped openings are exact, and only those are adjudicated.

**Players are not isolated.** They run as this user without a sandbox, so a player can write into its opponent's pipes through /proc (making it appear to name 1), signal or trace it, or change files. Results are meaningful only when every player is a trusted program.

- Players: book, exact, smallest, random (commands and digests in `plan.json`).
- Openings: 15 (14 with a known outcome, 1 capped).
- Rules: name an integer in 2..1000 outside the semigroup; the player who must name 1 loses.
- Clock: 2.0 s CPU plus 0.1 s per legal move; setup up to 10.0 s CPU and 60.0 s wall, not charged; per-move wall limit 3 x remaining CPU + 5 s.
- CPU accounting: all 360 player seats in their own cgroup (cumulative cpu.stat usage of every descendant; cgroup.kill at game end).
- Games: 180 (180 decided, 0 void); seed 0; 4 parallel games.

## Standings

| Player | Group | Games | W | L | Score | Elo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| book | 1 | 90 | 77 | 13 | 85.6% | +458 |
| exact | 1 | 90 | 73 | 17 | 81.1% | +413 |
| smallest | 2 | 90 | 20 | 70 | 22.2% | -377 |
| random | 2 | 90 | 10 | 80 | 11.1% | -493 |

Elo is a Bradley–Terry rating (0.5 virtual wins and losses per player against a fixed anchor) with mean zero. **Rating gaps between groups are set by the prior, not by the games.** The win graph is not strongly connected (Ford's condition fails): every game between two groups was won by the higher group, so without the prior the gap between groups would be infinite, and it widens without bound as the prior shrinks. Only the order of the groups is data. A gap below is the lowest rating in the higher group minus the highest in the lower group.

| Groups | Gap at prior 0.5 | Gap at prior 0.05 |
| --- | ---: | ---: |
| 1 over 2 | +790 | +1170 |

Within a group the games determine the differences; intervals hold the 2.5–97.5 percentiles of 200 bootstrap resamples of the decided games.

| Pair in one group | Score | Elo difference | 95% interval |
| --- | ---: | ---: | ---: |
| book − exact | 17–13 | +45 | [-84, +199] |
| smallest − random | 20–10 | +116 | [-26, +252] |

## Head to head

Wins–losses of the row player against the column player, over both seats and all openings.

|  | book | exact | smallest | random |
| --- | ---: | ---: | ---: | ---: |
| book | — | 17–13 | 30–0 | 30–0 |
| exact | 13–17 | — | 30–0 | 30–0 |
| smallest | 0–30 | 0–30 | — | 20–10 |
| random | 0–30 | 0–30 | 10–20 | — |

## Loss reasons

| Player | opponent-must-name-1 |
| --- | ---: |
| book | 13 |
| exact | 17 |
| smallest | 70 |
| random | 80 |

## Openings with a known outcome

Outcome is for the player to move under perfect play (N: the first player should win; P: the second). Capped play is exact here. Each outcome comes from the source in the opening's note in `plan.json`: the Python reference solver for enders, the frozen exact cache for database openings.

| Opening | Start | Outcome | Frobenius | Perfect-play winner won |
| --- | --- | --- | ---: | ---: |
| ender-4-5 | {4,5} | N | 11 | 7/12 |
| ender-4-7 | {4,7} | N | 17 | 8/12 |
| ender-5-6 | {5,6} | N | 19 | 7/12 |
| ender-5-7 | {5,7} | N | 23 | 7/12 |
| ender-6-7 | {6,7} | N | 29 | 7/12 |
| ender-7-8 | {7,8} | N | 41 | 8/12 |
| db-0-60-P0 | {16,20,22,25,26,30} | P | 59 | 6/12 |
| db-0-60-N0 | {8,10,14,35} | N | 47 | 7/12 |
| db-60-100-P0 | {16,20,22,26,34,57} | P | 87 | 7/12 |
| db-60-100-N0 | {10,16,23,38} | N | 67 | 6/12 |
| db-100-140-P0 | {16,26,38,50,60,62,89,133,145} | P | 135 | 6/12 |
| db-100-140-N0 | {16,26,28,36,38,46,115,123,127,137,145} | N | 135 | 5/12 |
| db-140-180-P0 | {16,26,30,38,40,44,50,107,121,125,129,131} | P | 143 | 6/12 |
| db-140-180-N0 | {16,26,73,82,86,88,127,133,139} | N | 145 | 6/12 |

| Player | Won when it should win | Won when it should lose |
| --- | ---: | ---: |
| book | 41/42 | 32/42 |
| exact | 38/42 | 29/42 |
| smallest | 9/42 | 9/42 |
| random | 5/42 | 5/42 |

## Openings without adjudication

Capped or of unknown outcome: these results measure the programs, not the position.

| Opening | Start | Capped | Games | First player won |
| --- | --- | --- | ---: | ---: |
| empty | {} | yes | 12 | 6 |

## CPU per move

| Player | Moves | Mean CPU (s) | Max CPU (s) | Mean setup CPU (s) |
| --- | ---: | ---: | ---: | ---: |
| book | 677 | 0.069 | 1.879 | 0.554 |
| exact | 692 | 0.074 | 2.031 | 0.082 |
| smallest | 110 | 0.000 | 0.001 | 0.082 |
| random | 286 | 0.000 | 0.001 | 0.082 |

## Blunders (exact analysis, Frobenius number at most 150)

A blunder is a move from an N-position to an N-position. Positions were solved by the native solver, 60 s each: 597 positions, 7 unknown after the limit. Analysis CPU was 1442.3 s; it never affects results.

| Player | Analysed moves | From N | Blunders | Blunder rate | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| book | 438 | 322 | 24 | 7.5% | 6 |
| exact | 433 | 270 | 34 | 12.6% | 5 |
| smallest | 102 | 70 | 52 | 74.3% | 3 |
| random | 246 | 91 | 75 | 82.4% | 6 |

## Void games

None.

## Limitations

- A same-user process can move itself out of its cgroup and so escape both the clock and the kill at game end.
- Players run as the same user without a sandbox; see the warning at the top.
- CPU timings depend on the machine and its load, and the exact players stop searching when their budget ends, so a rerun need not reproduce every game.

## Reproduce

```sh
python -m sylver.arena league --output /tmp/league-pilot --players random,smallest,exact,book --suites empty,enders,database --per-band 1 --workers 4 --analyze-bound 150 --seed 0
```
