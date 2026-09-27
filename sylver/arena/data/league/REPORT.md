# Game arena league

**Game results are not proofs.** A win, a rating, or a win rate here is evidence about these programs under these clocks, never about the outcome of a position. Openings are *capped* unless they have gcd one and a Frobenius number at most the move cap 1000; the empty position is capped. Capped games follow a house rule: moves are limited to 2..1000, which never ends a game early but removes larger moves, so their games say nothing about real Sylver Coinage. Only uncapped openings are exact, and only those are adjudicated.

**Players are sandboxed** (landlock): each can read only its own files (built-ins: the checkout, the interpreter, and the solver) and write only a scratch directory, and cannot read other processes' /proc entries, signal or trace them, or leave its cgroup. Path existence and metadata remain visible; see sylver/arena/README.md for the backend guarantees.

- Players: book, exact, smallest, random (commands and digests in `plan.json`).
- Openings: 15 (14 with a known outcome, 1 capped).
- Rules: name an integer in 2..1000 outside the semigroup; the player who must name 1 loses.
- Clock: 2.0 s CPU plus 0.1 s per legal move; setup up to 10.0 s CPU and 60.0 s wall, not charged; per-move wall limit 3 x remaining CPU + 5 s.
- CPU accounting: all 360 player seats in their own cgroup (cumulative cpu.stat usage of every descendant; cgroup.kill at game end).
- Games: 180 (180 decided, 0 void); seed 0; 4 parallel games.

## Standings

| Player | Games | W | L | Score | Elo | 95% interval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| book | 90 | 74 | 16 | 82.2% | +277 | [+199, +388] |
| exact | 90 | 71 | 19 | 78.9% | +248 | [+171, +364] |
| smallest | 90 | 20 | 70 | 22.2% | -238 | [-315, -182] |
| random | 90 | 15 | 75 | 16.7% | -287 | [-415, -198] |

Elo is a Bradley–Terry rating (0.5 virtual wins and losses per player against a fixed anchor) with mean zero; the interval holds the 2.5–97.5 percentiles of 200 bootstrap resamples of the decided games.

## Head to head

Wins–losses of the row player against the column player, over both seats and all openings.

|  | book | exact | smallest | random |
| --- | ---: | ---: | ---: | ---: |
| book | — | 16–14 | 30–0 | 28–2 |
| exact | 14–16 | — | 30–0 | 27–3 |
| smallest | 0–30 | 0–30 | — | 20–10 |
| random | 2–28 | 3–27 | 10–20 | — |

## Loss reasons

| Player | cpu-time | opponent-must-name-1 |
| --- | ---: | ---: |
| book | 5 | 11 |
| exact | 7 | 12 |
| smallest | 0 | 70 |
| random | 0 | 75 |

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
| db-100-140-P0 | {16,26,38,50,60,62,89,133,145} | P | 135 | 7/12 |
| db-100-140-N0 | {16,26,28,36,38,46,115,123,127,137,145} | N | 135 | 5/12 |
| db-140-180-P0 | {16,26,30,38,40,44,50,107,121,125,129,131} | P | 143 | 7/12 |
| db-140-180-N0 | {16,26,73,82,86,88,127,133,139} | N | 145 | 4/12 |

| Player | Won when it should win | Won when it should lose |
| --- | ---: | ---: |
| book | 40/42 | 30/42 |
| exact | 38/42 | 28/42 |
| smallest | 9/42 | 9/42 |
| random | 6/42 | 8/42 |

## Openings without adjudication

Capped or of unknown outcome: these results measure the programs, not the position.

| Opening | Start | Capped | Games | First player won |
| --- | --- | --- | ---: | ---: |
| empty | {} | yes | 12 | 6 |

## CPU per move

| Player | Moves | Mean CPU (s) | Max CPU (s) | Mean setup CPU (s) |
| --- | ---: | ---: | ---: | ---: |
| book | 424 | 0.207 | 0.804 | 0.516 |
| exact | 440 | 0.247 | 0.815 | 0.126 |
| smallest | 110 | 0.000 | 0.001 | 0.123 |
| random | 279 | 0.000 | 0.001 | 0.124 |

## Blunders (exact analysis, Frobenius number at most 150)

A blunder is a move from an N-position to an N-position. Positions were solved by the native solver, 60 s each: 551 positions, 2 unknown after the limit. Analysis CPU was 1220.1 s; it never affects results.

| Player | Analysed moves | From N | Blunders | Blunder rate | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| book | 378 | 293 | 45 | 15.4% | 2 |
| exact | 374 | 258 | 57 | 22.1% | 2 |
| smallest | 102 | 73 | 55 | 75.3% | 0 |
| random | 239 | 100 | 81 | 81.0% | 2 |

## Void games

None.

## Limitations

- A same-user process can move itself out of its cgroup and so escape both the clock and the kill at game end.
- Players run as the same user without a sandbox; see the warning at the top.
- CPU timings depend on the machine and its load, and the exact players stop searching when their budget ends, so a rerun need not reproduce every game.

## Reproduce

```sh
python -m sylver.arena league --output /tmp/claude-1001/-home-ruclaw-src-sylver-coinage/cd9b0cdd-5710-4000-902b-0c5c9cdc90cc/scratchpad/league-sbx/league-pilot --players random,smallest,exact,book --suites empty,enders,database --per-band 1 --workers 4 --analyze-bound 150 --seed 0
```
