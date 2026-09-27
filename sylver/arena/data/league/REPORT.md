# Game arena league

**Game results are not proofs.** A win, a rating, or a win rate here is evidence about these programs under these clocks, never about the outcome of a position. Openings that are *capped* (gcd above one, or Frobenius number above the move cap 1000) follow a house rule: moves are limited to 2..1000, which never ends a game early but removes larger moves, so their games say nothing about real Sylver Coinage. Only openings with gcd one and Frobenius number at most the cap are exact, and only those are adjudicated.

- Players: book, exact, smallest, random (commands and digests in `plan.json`).
- Openings: 15 (14 with a known outcome, 1 capped).
- Rules: name an integer in 2..1000 outside the semigroup; the player who must name 1 loses.
- Clock: 2.0 s CPU plus 0.1 s per legal move; setup up to 10.0 s CPU and 60.0 s wall, not charged; per-move wall limit 3 x remaining CPU + 5 s.
- Games: 180 (180 decided, 0 void); seed 0; 4 parallel games.

## Standings

| Player | Games | W | L | Score | Elo | 95% interval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| book | 90 | 77 | 13 | 85.6% | +458 | [+397, +543] |
| exact | 90 | 73 | 17 | 81.1% | +413 | [+345, +486] |
| smallest | 90 | 20 | 70 | 22.2% | -377 | [-447, -316] |
| random | 90 | 10 | 80 | 11.1% | -493 | [-584, -415] |

Elo is a Bradley–Terry rating (MM, 0.5 virtual wins and losses against a fixed anchor) with mean zero; the interval holds the 2.5–97.5 percentiles of 200 bootstrap resamples of the decided games.

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
| book | 677 | 0.067 | 1.930 | 0.537 |
| exact | 692 | 0.073 | 2.030 | 0.070 |
| smallest | 110 | 0.000 | 0.010 | 0.071 |
| random | 286 | 0.000 | 0.010 | 0.070 |

CPU is sampled from /proc at clock-tick resolution (typically 10 ms), so very fast moves read as 0.

## Blunders (exact analysis, Frobenius number at most 150)

A blunder is a move from an N-position to an N-position. Positions were solved by the native solver, 60 s each: 597 positions, 4 unknown after the limit. Analysis CPU was 1412.7 s; it never affects results.

| Player | Analysed moves | From N | Blunders | Blunder rate | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| book | 438 | 326 | 27 | 8.3% | 2 |
| exact | 433 | 274 | 36 | 13.1% | 3 |
| smallest | 102 | 73 | 55 | 75.3% | 0 |
| random | 246 | 95 | 77 | 81.1% | 3 |

## Void games

None.

## Limitations

- A player is charged the CPU of the live processes in its session, including children it has reaped. A process that leaves its session (daemonizes with setsid) is neither charged nor killed at game end.
- External players run with resource limits but no filesystem sandbox, so leagues should include only trusted programs.
- CPU timings depend on the machine and its load, and the exact players stop searching when their budget ends, so a rerun need not reproduce every game.

## Reproduce

```sh
python -m sylver.arena league --output /tmp/league-pilot --players random,smallest,exact,book --suites empty,enders,database --per-band 1 --workers 4 --analyze-bound 150 --seed 0
```
