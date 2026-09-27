# Game arena: programs play Sylver Coinage against each other

Date: 2026-09-27
Status: approved design (autonomous session; the owner pre-authorized
design decisions and asked that work proceed without pausing)

## Context

The proof-search arena (#6–#12, PR #14) rates *proofs*: canonical
certificates, independently replayed, scored by `S=(C+100)*(T+1)`. The
owner's next goals are two kinds of competition between programs:

1. short certificate proofs built from the frozen outcome database
   (separate spec: certificate golf and "The Book"), and
2. **playing the game itself.**

This spec covers (2). Nothing here changes the proof referee, the episode
accountant, or any file pinned by a recorded verifier or execution
profile, so every archived arena artifact keeps its identity.

## What the owner said, and what is assumed

Said: compete programs against each other; one competition is playing
Sylver Coinage; push and merge PRs; the machine has ample memory and fair
CPU (12 logical CPUs, 62 GB).

Assumed (recorded here so they can be corrected later):

- A game result is a *game* result. No game, rating, or win rate is ever
  presented as a proof of any position's outcome.
- Player programs are untrusted processes speaking a line protocol, as in
  chess engine matches (UCI-like), so AI agents, C++ engines, and Python
  scripts can compete on equal terms.
- CPU time, not wall time, is the clock, consistent with the proof arena.

## Rules

Standard Sylver Coinage: players alternately name positive integers that
are not non-negative integer combinations of numbers already named; the
player who names 1 loses. A game may start from any position (the empty
position is the real game; `{16}` is Conway's open question).

**Move cap.** Every game records `max_move = M >= 3` (default 1000); moves
must satisfy `1 <= n <= M`. For a gcd-one position whose Frobenius number
is at most M, capped play is *exactly* Sylver Coinage. Otherwise the cap
is a house rule and reports say "capped". The cap never ends a game
early: if the semigroup contains every integer in `[2, M]` it contains 2
and 3, hence every integer above 1. So the game is over — the player to
move must name 1 — **exactly when 2 and 3 both lie in the semigroup.**
This makes the referee's state one `M+1`-bit membership set.

**Losses.** Naming 1; naming an illegal, out-of-range, or malformed move;
exceeding the CPU clock or the wall-time safety limit; crashing or
closing the pipe; failing the setup handshake. The winner of a game that
reaches `{2,3} ⊆ S` is the player who made the last move.

## Protocol (schema 1, JSON Lines over stdin/stdout)

The referee writes one object per line; the player answers `move`
requests with one line.

```text
-> {"type":"hello","schema":1,"rules":{"max_move":M},"seat":"first"|"second","clock":{...}}
<- {"type":"ready","name":"...","version":"..."}          (optional fields)
-> {"type":"move","schema":1,"game":ID,"start":[...],"history":[...],
    "generators":[...],"gcd":d,"seat":"first","ply":k,
    "clock":{"cpu_remaining":x,"cpu_increment":y,"opponent_cpu_remaining":z}}
<- {"move":n,"claim":"win"|"loss"|"unknown","note":"<=200 chars"}   (claim/note optional)
-> {"type":"end","winner":"first"|"second","reason":"..."}
```

`generators` are the canonical minimal generators of the current
semigroup; `history` is every number named since `start`, in order.
Stdout carries protocol lines only; players log to stderr.

## Clocks and accounting

Each player gets `cpu_base` seconds (default 2.0) plus a Fischer
increment (default 0.1 s) credited after each legal move. One fresh
process per player per game, started in its own session. Setup (process
start and the hello/ready handshake, e.g. loading a database) is measured
and capped separately (`setup_cpu`, default 10 s) but not charged to the
game clock, like engine initialisation in chess.

Per-move CPU is the change in
`Σ over live processes in the player's session of (utime+stime+cutime+cstime)`
from `/proc`, which includes children the player has reaped, such as an
exact solver subprocess. Each move also has a wall-time safety limit
(`3 × cpu_remaining + 5 s`) so a sleeping player cannot stall a match.
Players are killed (whole session) at game end. **Known limitation:** a
process that daemonizes out of the session is not charged per move; the
report says so. External players run with resource limits but no
filesystem sandbox in this first version, so leagues should include only
trusted programs; wrapping them in the arena's sandbox launcher is a
follow-up once that launcher works on hosts without unprivileged user
namespaces (see the arena hardening work).

## Built-in players

All deterministic given a seed; all run through the same protocol as
external programs (`python -m sylver.arena.players NAME`).

| Player | Behaviour |
| --- | --- |
| `random` | Uniform legal move in `[2, M]`. |
| `smallest` | Smallest legal move ≥ 2 (weak control). |
| `exact` | Finite position with Frobenius ≤ `exact_bound`: exact native solve within its clock; plays a winning move, or when lost the move whose child has the largest Frobenius number ("complicate"). Otherwise a bounded *witness search*: children that become finite and small are solved in increasing Frobenius order, playing the first P child found; fallback "complicate". |
| `book` | `exact`, preceded by a lookup of every legal move's child in the frozen outcome database (305,011 exact rows plus certified campaign facts); a known P child is played at once. Opening theory: from the empty position it names a prime ≥ 5 (Hutchings). |

The native solver binary is built once before games, like the proof
arena's shared tools, and passed to players as an option.

## League

`python -m sylver.arena league` runs a round robin: every pair of players,
every opening, both seats; games run in parallel worker processes (default
4). Outputs, all in a new directory:

- `plan.json`: players (with command/option digests), openings, rules,
  clocks, seed — written before the first game;
- `games.jsonl`: one complete record per game (moves, per-move CPU and
  wall, claims, result, reason, setup costs);
- `standings.json` and `REPORT.md`: per-player score, a
  Bradley–Terry rating on the Elo scale with a bootstrap interval,
  head-to-head tables, loss reasons, and per-opening results.

**Opening suites.** `empty` (the real game); `enders` (small coprime
pairs, all N: the mover should win); `database` (finite positions sampled
reproducibly from the cache across Frobenius bands, balanced P/N, with
their exact outcomes); `research` (`{16}`, `{16,26}`, W, X — exhibition
only, outcomes unknown).

**Adjudication.** For openings with a known outcome the report shows how
often the player who *should* win under perfect play did win. Optional
post-game analysis (`--analyze-bound F`) exact-evaluates every reached
finite position with Frobenius ≤ F and counts **blunders** (a move from
an N-position to an N-position) per player. Analysis CPU is reported
separately and never affects results.

## Error handling

Every failure is a recorded, attributed loss with a reason string; the
referee never crashes a league because a player misbehaves. A referee
bug (an exception in the referee itself) marks the game `void` and is
listed separately; void games are excluded from ratings and counted in
the report.

## Testing

- Rules: legality, cap semantics, the `{2,3}` terminal criterion checked
  against exhaustive gap enumeration, canonical generators, naming 1.
- Referee: illegal/out-of-range/malformed moves, crash, silent player,
  CPU busy-loop loses on time, sleeping player loses on wall time,
  subprocess CPU is charged to the parent player.
- Players: deterministic replay with fixed seeds; `exact` never loses a
  won position it can solve (checked against the Python reference on
  small openings); `book` plays database P children.
- League: Bradley–Terry recovers a known ordering on synthetic results;
  report rendering; a tiny end-to-end league.

## Recorded pilot

A league of the four built-ins over `empty`, `enders`, and `database`
openings, with results and the report committed under
`sylver/arena/data/league/`. It is an engineering pilot: it measures the
harness and the built-ins, not the mathematics of any open position.

## Non-goals

No change to proof scoring, verifier sources, or recorded artifacts; no
paid model calls; no claim that any game result proves an outcome.
