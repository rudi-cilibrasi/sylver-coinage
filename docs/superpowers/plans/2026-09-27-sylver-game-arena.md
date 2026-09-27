# Game Arena Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Programs play Sylver Coinage against each other under CPU clocks, with a referee, four built-in players, round-robin leagues, ratings, and a recorded pilot.

**Architecture:** Pure rules in `game.py`; one referee process per game drives two untrusted player processes over JSON Lines (`referee.py`); built-in players share one host loop (`players.py`); `league.py` schedules games in parallel, rates players (Bradley–Terry), and renders a report. No file pinned by a proof-arena verifier or execution profile is modified.

**Tech Stack:** Python 3.11 standard library only; the existing C++ `sylver/native_solver.cpp` via `sylver.arena.exact.build_tools`; `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-27-sylver-game-arena-design.md`

## Global Constraints

- Do **not** modify: `sylver/arena/{proof,common,snapshot,exact,worker,episode,supervisor,protocol,policies,agent}.py`, `sylver/solver.py`, `sylver/short_certificates.py`, `sylver/native_solver.cpp`. (Their hashes are pinned by recorded profiles.) Only `sylver/arena/__main__.py`, `sylver/arena/README.md`, `README.md` may be edited among existing files.
- Standard library only. Python ≥ 3.11. Linux `/proc` required for clocks.
- Match the codebase style: compact modules, short docstrings stating invariants, `write`/`read`/`sha` helpers from `sylver.arena.common` for JSON artifacts (canonical JSON + trailing newline).
- Every output directory must be new (`mkdir()` without `exist_ok`), as elsewhere in the arena.
- Default rules: `max_move=1000`; clock `cpu_base=2.0`, `cpu_increment=0.1`, `setup_cpu=10.0`, `setup_wall=60.0`; per-move wall limit `3*cpu_remaining+5`.
- A game result is never described as a proof of an outcome (reports say so).
- Tests live in `tests/arena/test_game.py` and must run in < 3 minutes total; run with `python -m unittest tests.arena.test_game -v`.

## Review Focus

1. A player that writes its move and keeps computing (pondering) must have that CPU charged at its next measurement, not escape the clock — covered in Task 3 (`test_pondering_cpu_is_charged`).
2. A player that prints non-JSON, a JSON list, a float move, `true`, or a huge integer must lose with reason `malformed-move`/`illegal-move`, never crash the referee — Task 3 (`test_malformed_replies_lose`).
3. A player that exits or closes stdout mid-game loses with `crashed`; the opponent's process is still reaped (no zombies/orphans) — Task 3 (`test_crash_and_cleanup`).
4. The end test must be exact for starts that already contain 2 or 3 and for `max_move=3` — Task 1 (`test_end_iff_two_and_three`).
5. League output directories must be new and partial results must survive an interrupted league (games appended as they finish) — Task 4 (`test_league_writes_incrementally`).

---

### Task 1: Rules (`sylver/arena/game.py`)

**Files:**
- Create: `sylver/arena/game.py`
- Test: `tests/arena/test_game.py` (class `RulesTests`)

**Interfaces:**
- Produces: `DEFAULT_MAX_MOVE=1000`; `class IllegalMove(ValueError)`; `minimal_generators(values)->tuple[int,...]`; `class Position(start=(), history=(), max_move=1000)` with attributes `max_move:int`, `start:tuple`, `history:tuple`, `members:int` (bitset), `generators:tuple`, and methods `is_legal(n)->bool`, `play(n)->Position` (raises `IllegalMove`; never accepts 1), `over()->bool`, `gcd()->int` (0 for the empty position), `frobenius()->int|None` (None unless gcd 1), `capped()->bool`, `legal_moves()->list[int]` (ascending, excludes 1), `key()->str`.

- [ ] **Step 1: Write the failing tests**

```python
import itertools, random, unittest
from sylver.arena.game import IllegalMove, Position, minimal_generators
from sylver.solver import FiniteSolver


class RulesTests(unittest.TestCase):
    def test_minimal_generators(self):
        self.assertEqual(minimal_generators([8, 4, 6, 12]), (4, 6))
        self.assertEqual(minimal_generators([16, 26, 42]), (16, 26))
        self.assertEqual(minimal_generators([]), ())

    def test_members_and_legal_moves(self):
        p = Position([4, 6], max_move=20)
        self.assertEqual(p.legal_moves(), [2, 3, 5, 7, 9, 11, 13, 15, 17, 19])
        self.assertTrue(p.is_legal(1))
        self.assertFalse(p.is_legal(10))
        self.assertFalse(p.is_legal(21))
        for bad in (True, 0, -3, 2.0, '5', None):
            self.assertFalse(p.is_legal(bad))

    def test_play_is_immutable_and_canonical(self):
        p = Position([6, 9], max_move=100)
        q = p.play(4)
        self.assertEqual(p.generators, (6, 9))
        self.assertEqual(q.generators, (4, 6, 9))
        self.assertEqual(q.play(2).generators, (2, 9))
        self.assertEqual(q.history, (4,))
        with self.assertRaises(IllegalMove):
            q.play(10)
        with self.assertRaises(IllegalMove):
            q.play(1)

    def test_end_iff_two_and_three(self):
        rng = random.Random(7)
        for _ in range(300):
            m = rng.randint(3, 40)
            start = rng.sample(range(2, m + 1), rng.randint(1, 4))
            p = Position(start, max_move=m)
            gaps = [n for n in range(2, m + 1) if not p.members >> n & 1]
            self.assertEqual(p.over(), not gaps)
        self.assertTrue(Position([2, 3], max_move=3).over())
        self.assertFalse(Position([2], max_move=3).over())
        self.assertEqual(Position([2], max_move=3).legal_moves(), [3])

    def test_frobenius_gcd_and_cap(self):
        self.assertEqual(Position([5, 7]).frobenius(), 23)
        self.assertEqual(Position([]).gcd(), 0)
        self.assertEqual(Position([16, 26]).gcd(), 2)
        self.assertIsNone(Position([16, 26]).frobenius())
        self.assertFalse(Position([5, 7]).capped())
        self.assertTrue(Position([16]).capped())
        self.assertTrue(Position([31, 37], max_move=100).capped())

    def test_finite_play_matches_reference_gaps(self):
        for gens in ([4, 5], [5, 7], [6, 7, 11], [8, 9, 12]):
            p = Position(gens)
            s = FiniteSolver(gens)
            self.assertEqual(p.legal_moves(), list(s.legal_moves(s.initial_state)))

    def test_rejects_bad_rules(self):
        for m in (2, True, 10.0, 1 << 21):
            with self.assertRaises(ValueError):
                Position([], max_move=m)
        with self.assertRaises(ValueError):
            Position([1])
        with self.assertRaises(ValueError):
            Position([1001])
```

- [ ] **Step 2: Run to verify failure** — `python -m unittest tests.arena.test_game.RulesTests -v` → `ModuleNotFoundError: sylver.arena.game`.

- [ ] **Step 3: Implement `sylver/arena/game.py`**

```python
"""Sylver Coinage rules for arena play: capped moves and an exact end test.

Bit n of ``members`` is set exactly when n (0 <= n <= max_move) lies in the
semigroup generated by the named numbers. The player to move must name 1,
and so loses, exactly when 2 and 3 are members: if every integer in
[2, max_move] were a member, 2 and 3 would be, and 2a+3b covers every
integer above 1. A move cap therefore never ends a game early; it only
removes larger moves, and play is exact Sylver Coinage whenever the
position has gcd one and Frobenius number at most the cap.
"""
from functools import reduce
from math import gcd

from sylver.solver import frobenius_number

DEFAULT_MAX_MOVE = 1000
MAX_MOVE_LIMIT = 1 << 20


class IllegalMove(ValueError):
    """Not a legal move of at least 2 in this position."""


def _adjoin(bits, move, limit):
    mask = (1 << (limit + 1)) - 1
    shift = move
    while shift <= limit:
        bits |= (bits << shift) & mask
        shift *= 2
    return bits


def minimal_generators(values):
    values = sorted(set(values))
    result, bits = [], 1
    top = values[-1] if values else 0
    for v in values:
        if not bits >> v & 1:
            result.append(v)
            bits = _adjoin(bits, v, top)
    return tuple(result)


class Position:
    """Immutable: the start generators, the moves named since, and the cap."""
    __slots__ = ('max_move', 'start', 'history', 'members', 'generators')

    def __init__(self, start=(), history=(), max_move=DEFAULT_MAX_MOVE):
        if type(max_move) is not int or not 3 <= max_move <= MAX_MOVE_LIMIT:
            raise ValueError(f'max_move must be an integer in [3, {MAX_MOVE_LIMIT}]')
        if any(type(v) is not int or not 2 <= v <= max_move for v in start):
            raise ValueError('start generators must be integers in [2, max_move]')
        self.max_move = max_move
        self.start = minimal_generators(start)
        self.history = ()
        self.generators = self.start
        members = 1
        for v in self.start:
            members = _adjoin(members, v, max_move)
        self.members = members
        position = self
        for move in history:
            position = position.play(move)
        self.history, self.members, self.generators = position.history, position.members, position.generators

    def is_legal(self, n):
        return type(n) is int and 1 <= n <= self.max_move and not self.members >> n & 1

    def play(self, n):
        if n == 1 or not self.is_legal(n):
            raise IllegalMove(f'{n!r} is not a legal move of at least 2')
        child = object.__new__(Position)
        child.max_move, child.start = self.max_move, self.start
        child.history = self.history + (n,)
        child.members = _adjoin(self.members, n, self.max_move)
        child.generators = minimal_generators(self.generators + (n,))
        return child

    def over(self):
        return self.members & 0b1100 == 0b1100

    def gcd(self):
        return reduce(gcd, self.generators, 0)

    def frobenius(self):
        return frobenius_number(self.generators) if self.gcd() == 1 else None

    def capped(self):
        return self.gcd() != 1 or self.frobenius() > self.max_move

    def legal_moves(self):
        free = ~self.members & ((1 << (self.max_move + 1)) - 1) & ~0b11
        moves = []
        while free:
            low = free & -free
            moves.append(low.bit_length() - 1)
            free ^= low
        return moves

    def key(self):
        return ','.join(map(str, self.generators))
```

- [ ] **Step 4: Run to verify pass** — `python -m unittest tests.arena.test_game.RulesTests -v` → all PASS.

- [ ] **Step 5: Commit** — `git add sylver/arena/game.py tests/arena/test_game.py && git commit -m "Add capped Sylver Coinage rules for arena play"`

---

### Task 2: Built-in players and the host loop (`sylver/arena/players.py`)

**Files:**
- Create: `sylver/arena/players.py`
- Test: `tests/arena/test_game.py` (class `PlayerTests`)

**Interfaces:**
- Consumes: `Position`, `minimal_generators` from Task 1; `sylver.solver.frobenius_number`, `sylver.solver.solve_position`.
- Produces: `PLAYERS: dict[str, type[Player]]` with keys `random, smallest, exact, book`; `class Player(seed=0, options=None)` with `setup(hello)->None` and `choose(position, request)->int`; `builtin_command(name, seed=0, options=None)->list[str]` returning `[sys.executable, '-m', 'sylver.arena.players', name, '--seed', str(seed), '--options', json.dumps(options or {}, sort_keys=True)]`; `load_book(max_move)->dict[str,str]` (key → 'P'/'N'); module entry `main(argv=None)` implementing the protocol loop.

Behaviour (exact):

- Host loop: read stdin lines; `hello` → `player.setup(msg)` then print `{"type":"ready","name":NAME,"version":"1"}`; `move` → rebuild `Position(msg['start'], msg['history'], msg['rules']['max_move'])`, call `choose`, print `{"move":n,"claim":...}` (claim optional, from `player.last_claim`); `end` → exit 0. Flush after each line. Never print anything else to stdout.
- `random`: `self.rng.choice(position.legal_moves())`, `rng=random.Random(seed)`.
- `smallest`: `position.legal_moves()[0]`.
- `exact` options: `binary` (path to native solver, optional), `exact_bound` (default 180 with binary else 60), `time_share` (0.25), `memory_mb` (2048). Per move budget `min(cpu_remaining*time_share, cpu_remaining-0.25)` measured with `sum(os.times()[:4])` (includes reaped children). Order: (1) `opening(position)` hook (returns None in `exact`); (2) if gcd 1 and Frobenius ≤ bound: solve; N → play winning move with `claim='win'`; P → `complicate` with `claim='loss'`; (3) witness search: legal moves `m ≤ exact_bound + min(generators)` (skip when there are no generators) whose child is gcd 1 with Frobenius ≤ bound, in increasing (Frobenius, m) order, solving each until budget ends; first P child is played with `claim='win'`; (4) `complicate` with `claim='unknown'`.
- Solving: native `subprocess.run([binary, *gens], capture_output=True, text=True, timeout=remaining, preexec_fn=<RLIMIT_AS memory_mb>)`; parse `P winning_move=none ...` / `N winning_move=K ...`; timeout or failure → None (unknown). Without a binary, `solve_position` (Python) is used and the bound is 60. Results are memoised per game in `self.known`.
- `complicate`: sample up to 16 legal moves with the seeded rng plus the largest legal move; choose the one maximising `(child_gcd != 1, child_frobenius or 0, m)`.
- `book` = `exact` + `setup` loads `load_book(max_move)` (the 305,011-row cache `sylver/move26_data/periodicity_x.cache` as P/N plus THEORY facts) and, before step (2), plays any legal move `m ≤ max(book values)` whose child key is a book P, with `claim='win'`.
- THEORY facts (P, uncapped game): `{p}` for every prime `5 ≤ p ≤ max_move` (Hutchings); `{2,3}` (terminal); `{4,6}`; `{8,12}` (Blok); `{8,10,22}` (Sicherman); `{12,16,22}`, `{16,20,34}`, `{10,16,24}` (published, independently confirmed here); `{16,26,36,56}` (Sicherman's table; certified here); `{16,26,56,62,66}` (B, PR #4); `{16,26,62,85,98,134}` and `{16,26,62,95,98,102}` (PRs #5, #13). Each entry carries a one-line source comment.

- [ ] **Step 1: Write the failing tests**

```python
import io, json, subprocess, sys
from sylver.arena.game import Position
from sylver.arena.players import PLAYERS, builtin_command, load_book
from sylver.arena.exact import build_tools
from sylver.solver import solve_position


def request(position, cpu=5.0, seat='first'):
    return {'type': 'move', 'schema': 1, 'game': 't', 'start': list(position.start),
            'history': list(position.history), 'generators': list(position.generators),
            'gcd': position.gcd(), 'seat': seat, 'ply': len(position.history) + 1,
            'rules': {'max_move': position.max_move},
            'clock': {'cpu_remaining': cpu, 'cpu_increment': 0.1, 'opponent_cpu_remaining': cpu}}


class PlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = str(build_tools('/tmp/sylver-arena-tools'))

    def test_random_is_seeded_and_legal(self):
        p = Position([5, 7])
        a = PLAYERS['random'](seed=3); b = PLAYERS['random'](seed=3)
        moves = [a.choose(p, request(p)) for _ in range(5)]
        self.assertEqual(moves, [b.choose(p, request(p)) for _ in range(5)])
        self.assertTrue(all(p.is_legal(m) and m != 1 for m in moves))

    def test_exact_plays_a_winning_move(self):
        for gens in ([4, 5], [5, 7], [6, 7, 11], [8, 9, 12], [7, 9, 11]):
            p = Position(gens)
            if not solve_position(gens).is_winning:
                continue
            move = PLAYERS['exact'](options={'binary': self.binary}).choose(p, request(p))
            self.assertFalse(solve_position(p.play(move).generators).is_winning, (gens, move))

    def test_exact_witness_search_from_infinite_position(self):
        p = Position([6])            # {6} is N: reply 4 reaches {4,6} (gcd 2, not finite);
        move = PLAYERS['exact'](options={'binary': self.binary}).choose(p, request(p))
        self.assertTrue(p.is_legal(move))   # only legality is required here

    def test_book_plays_theory_and_database(self):
        book = PLAYERS['book'](options={'binary': self.binary})
        book.setup({'rules': {'max_move': 1000}})
        empty = Position([])
        self.assertEqual(book.choose(empty, request(empty)), 5)
        self.assertEqual(load_book(1000)['5'], 'P')
        p = Position([16, 26, 62, 98, 102])
        self.assertEqual(book.choose(p, request(p)), 95)   # {16,26,62,95,98,102} is P

    def test_host_protocol_round_trip(self):
        p = Position([4, 5])
        lines = [json.dumps({'type': 'hello', 'schema': 1, 'rules': {'max_move': 1000}, 'seat': 'first', 'clock': {}}),
                 json.dumps(request(p)), json.dumps({'type': 'end', 'winner': 'first', 'reason': 'x'})]
        out = subprocess.run(builtin_command('smallest'), input='\n'.join(lines) + '\n',
                             capture_output=True, text=True, timeout=30, check=True)
        replies = [json.loads(x) for x in out.stdout.splitlines()]
        self.assertEqual(replies[0]['type'], 'ready')
        self.assertEqual(replies[1]['move'], 2)
```

- [ ] **Step 2: Run to verify failure** — `python -m unittest tests.arena.test_game.PlayerTests -v` → ImportError.
- [ ] **Step 3: Implement `sylver/arena/players.py`** per the behaviour above (argparse: `name`, `--seed`, `--options` JSON).
- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git commit -m "Add built-in game players: random, smallest, exact, book"`

---

### Task 3: Referee (`sylver/arena/referee.py`)

**Files:**
- Create: `sylver/arena/referee.py`
- Test: `tests/arena/test_game.py` (class `RefereeTests`)

**Interfaces:**
- Consumes: `Position`, `IllegalMove` (Task 1); `builtin_command` (Task 2); `sylver.arena.common.write/sha`.
- Produces: `CLOCK = {'cpu_base':2.0,'cpu_increment':0.1,'setup_cpu':10.0,'setup_wall':60.0}`; `session_cpu(sid, outside:set)->tuple[float,list[int]]`; `play_game(first:dict, second:dict, output:Path, start=(), max_move=1000, clock=None, game_id='game') -> dict` where each player dict is `{'name': str, 'command': list[str]}` (optional `'cwd'`, `'env'`, `'memory_mb'` default 4096). Returns the record and writes it to `output/record.json`; player stderr goes to `output/{seat}.stderr` (last 64 KiB kept).

Record schema (exact keys): `schema, game, rules{max_move,loser:'names-1'}, start, players{first,second}{name,command_sha256}, clock, setup{seat:{cpu,wall,ready}}, moves[{ply,seat,move,cpu,wall,claim,note}], result{winner,loser,reason,detail}, final{generators,capped,over}, cpu_totals{first,second}`.

Loss reasons (exact strings): `named-1`, `illegal-move`, `malformed-move`, `cpu-time`, `wall-time`, `crashed`, `setup-failed`, `setup-cpu`. Win by `opponent-must-name-1` when the position is over after a move. Referee exceptions → `result.winner=None, reason='void'` with the traceback text in `detail`.

Key code (use as written):

```python
def session_cpu(sid, outside):
    """CPU seconds of live processes in session ``sid``, including reaped children."""
    ticks = os.sysconf('SC_CLK_TCK'); total = 0.0; members = []
    for name in os.listdir('/proc'):
        if not name.isdigit() or int(name) in outside:
            continue
        try:
            raw = Path('/proc', name, 'stat').read_bytes().decode()
        except OSError:
            continue
        f = raw[raw.rindex(')') + 2:].split()
        if int(f[3]) != sid:
            outside.add(int(name)); continue
        total += sum(int(f[i]) for i in (11, 12, 13, 14)) / ticks
        members.append(int(name))
    return total, members


class Channel:
    """JSON Lines over a pipe with a wall-clock deadline per message."""
    def __init__(self, proc):
        self.proc, self.buffer = proc, b''
    def send(self, message):
        self.proc.stdin.write(json.dumps(message, sort_keys=True).encode() + b'\n')
        self.proc.stdin.flush()
    def receive(self, seconds, check=lambda: None):
        """``check`` runs about every 50 ms while waiting; it raises to stop
        waiting early (the referee uses it to enforce the CPU clock)."""
        deadline = time.monotonic() + seconds; fd = self.proc.stdout.fileno()
        while b'\n' not in self.buffer:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError('no reply before the wall-time limit')
            if not select.select([fd], [], [], min(left, .05))[0]:
                check()
                continue
            chunk = os.read(fd, 65536)
            if not chunk:
                raise EOFError('player closed its output')
            self.buffer += chunk
            if len(self.buffer) > 1 << 20:
                raise ValueError('oversized reply')
        line, self.buffer = self.buffer.split(b'\n', 1)
        return json.loads(line)
```

Clock rule (checked **before** the reply is validated): charge `used = cpu_now - cpu_last` (all CPU since the previous measurement of that player, so CPU spent pondering during the opponent's turn is charged); `remaining -= used`; if `remaining < 0` → `cpu-time`; else, after a legal move, `remaining += cpu_increment`. While waiting for a reply, `check` recomputes the session CPU and raises as soon as `remaining` would go negative, so a busy player loses on time without waiting for the wall limit. Then move validation: reply must be a JSON object whose `move` has `type(...) is int`; otherwise `malformed-move`. `move == 1` → `named-1`; `not position.is_legal(move)` → `illegal-move`. The per-move wall limit is `3*remaining + 5` seconds. Setup: send `hello`, wait `setup_wall` for `ready`; setup CPU above `setup_cpu` → `setup-cpu`; the game clock starts after setup. End: send `end` to both (ignore broken pipes), then SIGKILL every member of each session (`os.killpg(pid, SIGKILL)` plus members from `session_cpu`), `wait()` both.

- [ ] **Step 1: Write the failing tests** (scripted players are tiny Python programs written to a temp dir)

```python
import tempfile, textwrap
from pathlib import Path
from sylver.arena.referee import play_game

SCRIPT = textwrap.dedent('''
    import json, sys, time, subprocess
    MODE = sys.argv[1]
    for line in sys.stdin:
        msg = json.loads(line)
        if msg["type"] == "hello":
            print(json.dumps({"type": "ready", "name": MODE}), flush=True)
        elif msg["type"] == "move":
            if MODE == "one": print(json.dumps({"move": 1}), flush=True)
            elif MODE == "illegal": print(json.dumps({"move": msg["generators"][0]}), flush=True)
            elif MODE == "garbage": print("not json", flush=True)
            elif MODE == "float": print(json.dumps({"move": 2.0}), flush=True)
            elif MODE == "crash": sys.exit(3)
            elif MODE == "sleep": time.sleep(60)
            elif MODE == "burn":
                t = time.process_time()
                while time.process_time() - t < 5: pass
            elif MODE == "child":
                subprocess.run([sys.executable, "-c", "import time\\nt=time.process_time()\\nwhile time.process_time()-t<1.5:pass"])
                print(json.dumps({"move": 2}), flush=True)
            elif MODE == "ponder":
                # 49 is a gap of <40,41>; the opponent then gets a turn, so the
                # CPU burned after this reply must be charged at our next turn.
                print(json.dumps({"move": 49}), flush=True)
                t = time.process_time()
                while time.process_time() - t < 1.5: pass
        else:
            break
''')


class RefereeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.dir = Path(self.tmp.name)
        (self.dir / 'p.py').write_text(SCRIPT)
    def tearDown(self):
        self.tmp.cleanup()
    def scripted(self, mode):
        return {'name': mode, 'command': [sys.executable, str(self.dir / 'p.py'), mode]}
    def smallest(self):
        return {'name': 'smallest', 'command': builtin_command('smallest')}
    def game(self, first, second, start=(4, 5), clock=None, name='g'):
        return play_game(first, second, self.dir / name, start=start,
                         clock=clock or {'cpu_base': 1.0, 'cpu_increment': 0.0, 'setup_cpu': 10.0, 'setup_wall': 30.0})

    def test_losses_are_attributed(self):
        for mode, reason in (('one', 'named-1'), ('illegal', 'illegal-move'), ('garbage', 'malformed-move'),
                             ('float', 'malformed-move'), ('crash', 'crashed'), ('burn', 'cpu-time')):
            r = self.game(self.scripted(mode), self.smallest(), name=mode)
            self.assertEqual((r['result']['loser'], r['result']['reason']), ('first', reason), mode)

    def test_sleeping_player_loses_on_wall_time(self):
        r = self.game(self.scripted('sleep'), self.smallest(), clock={'cpu_base': .2, 'cpu_increment': 0., 'setup_cpu': 10., 'setup_wall': 30.})
        self.assertEqual(r['result']['reason'], 'wall-time')

    def test_child_process_cpu_is_charged(self):
        r = self.game(self.scripted('child'), self.smallest())
        self.assertEqual((r['result']['loser'], r['result']['reason']), ('first', 'cpu-time'))

    def test_pondering_cpu_is_charged(self):
        r = self.game(self.scripted('ponder'), self.smallest(), start=(40, 41))
        self.assertEqual((r['result']['loser'], r['result']['reason']), ('first', 'cpu-time'))

    def test_normal_game_record(self):
        r = self.game(self.smallest(), self.smallest(), start=(4, 5))
        self.assertEqual(r['result']['reason'], 'opponent-must-name-1')
        self.assertTrue(r['final']['over'])
        self.assertEqual([m['move'] for m in r['moves']], [2, 3])   # {4,5}+2 -> {2,5}; +3 -> {2,3}
        self.assertEqual(r['result']['winner'], 'second')
        self.assertTrue((self.dir / 'g/record.json').exists())

    def test_crash_and_cleanup(self):
        r = self.game(self.scripted('crash'), self.smallest(), name='c')
        self.assertEqual(r['result']['reason'], 'crashed')
        out = subprocess.run(['pgrep', '-f', str(self.dir / 'p.py')], capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), '')

    def test_malformed_replies_lose(self):
        r = self.game(self.scripted('garbage'), self.smallest(), name='m')
        self.assertEqual(r['result']['reason'], 'malformed-move')
```

- [ ] **Step 2: Run to verify failure** — `python -m unittest tests.arena.test_game.RefereeTests -v` → ImportError.
- [ ] **Step 3: Implement `sylver/arena/referee.py`** with the code above plus `play_game`.
- [ ] **Step 4: Run to verify pass.**
- [ ] **Step 5: Commit** — `git commit -m "Add the game referee with per-session CPU clocks"`

---

### Task 4: League, ratings, analysis, report (`sylver/arena/league.py`)

**Files:**
- Create: `sylver/arena/league.py`
- Test: `tests/arena/test_game.py` (class `LeagueTests`)

**Interfaces:**
- Consumes: `play_game`, `CLOCK` (Task 3); `builtin_command`, `PLAYERS` (Task 2); `Position` (Task 1); `sylver.arena.exact.build_tools`.
- Produces: `ENDERS`, `suite(name, seed=0, per_band=1)->list[dict]` (opening dicts `{'name','start','outcome','note'}`; names `empty|enders|database|research`); `bradley_terry(results, players, prior=0.5)->dict[str,float]` (Elo scale, mean 0; `results` is a list of `(winner, loser)`); `run_league(players:dict[str,dict], openings:list[dict], output:Path, max_move=1000, clock=None, workers=4, seed=0, analyze_bound=0)->dict`; `render(plan, games, standings)->str`.

Rules for `run_league`: create `output` (must be new); write `plan.json` first (players with `command_sha256`, openings, rules, clock, seed, workers); schedule every opening × ordered pair (a≠b), game id `f'{i:04d}-{opening}-{a}-vs-{b}'`, seed offset `seed+i` passed to built-ins; run with `concurrent.futures.ProcessPoolExecutor(workers)`; append each finished record to `games.jsonl` immediately; after all games write `standings.json` and `REPORT.md`. Ratings exclude void games. Bootstrap intervals: 200 resamples of the decided games with `random.Random(seed)`, 2.5/97.5 percentiles. Analysis (`analyze_bound>0`): for every move from a gcd-one position with Frobenius ≤ bound, evaluate the position before and after the move with the native solver (cache by key, 60 s timeout each, unknown on timeout); a *blunder* is N-before and N-after. Report sections: scope note ("game results are not proofs"), standings (player, games, W, L, score %, Elo, 95% interval), head-to-head matrix, loss reasons, openings with a known outcome ("perfect-play winner won k/n"), per-move CPU (mean, max) per player, blunders (if analysed), void games, reproduction command.

Bradley–Terry (use as written):

```python
def bradley_terry(results, players, prior=0.5, iterations=5000):
    """MM iterations (Hunter 2004) with `prior` virtual wins and losses
    against a fixed anchor of strength 1, so undefeated or winless players
    get finite ratings. Returned on the Elo scale with mean zero."""
    wins = {p: prior for p in players}; pairs = {}
    for w, l in results:
        wins[w] += 1; k = tuple(sorted((w, l))); pairs[k] = pairs.get(k, 0) + 1
    s = {p: 1.0 for p in players}
    for _ in range(iterations):
        new = {}
        for p in players:
            d = 2 * prior / (s[p] + 1.0)
            for q in players:
                if q != p:
                    n = pairs.get(tuple(sorted((p, q))), 0)
                    if n: d += n / (s[p] + s[q])
            new[p] = wins[p] / d
        done = max(abs(new[p] - s[p]) for p in players) < 1e-12; s = new
        if done: break
    elo = {p: 400 * math.log10(s[p]) for p in players}
    mean = sum(elo.values()) / len(elo)
    return {p: elo[p] - mean for p in players}
```

- [ ] **Step 1: Write the failing tests**

```python
from sylver.arena.league import ENDERS, bradley_terry, render, run_league, suite


class LeagueTests(unittest.TestCase):
    def test_bradley_terry_orders_players(self):
        results = [('a', 'b')] * 8 + [('b', 'a')] * 2 + [('b', 'c')] * 8 + [('c', 'b')] * 2 + [('a', 'c')] * 9 + [('c', 'a')]
        r = bradley_terry(results, ['a', 'b', 'c'])
        self.assertGreater(r['a'], r['b']); self.assertGreater(r['b'], r['c'])
        self.assertAlmostEqual(sum(r.values()), 0, places=6)
        r = bradley_terry([('a', 'b')] * 5, ['a', 'b'])
        self.assertTrue(all(math.isfinite(v) for v in r.values()))

    def test_suites(self):
        self.assertEqual(suite('empty')[0]['start'], [])
        self.assertTrue(all(o['outcome'] == 'N' for o in suite('enders')))
        db = suite('database', seed=0, per_band=1)
        self.assertEqual(len(db), 8)
        self.assertEqual(db, suite('database', seed=0, per_band=1))
        self.assertEqual({o['outcome'] for o in db}, {'P', 'N'})

    def test_league_writes_incrementally(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'league'
            players = {n: {'name': n, 'command': builtin_command(n)} for n in ('smallest', 'random')}
            standings = run_league(players, suite('enders')[:2], out, workers=2,
                                   clock={'cpu_base': 2.0, 'cpu_increment': 0.1, 'setup_cpu': 10.0, 'setup_wall': 30.0})
            lines = (out / 'games.jsonl').read_text().splitlines()
            self.assertEqual(len(lines), 4)
            self.assertTrue((out / 'plan.json').exists() and (out / 'REPORT.md').exists())
            self.assertEqual(sum(v['games'] for v in standings['players'].values()), 8)
            with self.assertRaises(FileExistsError):
                run_league(players, suite('enders')[:1], out)
```

- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3: Implement `sylver/arena/league.py`.** Built-in players whose name is `exact` or `book` receive `options={'binary': str(build_tools(output.parent / 'arena-tools'))}` when the league resolves them (the CLI does this; tests pass explicit commands).
- [ ] **Step 4: Run to verify pass.**
- [ ] **Step 5: Commit** — `git commit -m "Add game leagues with Bradley-Terry ratings and reports"`

---

### Task 5: CLI, documentation, recorded pilot

**Files:**
- Modify: `sylver/arena/__main__.py` (add `play`, `league` subcommands only)
- Modify: `sylver/arena/README.md` (new section "Game arena"), `README.md` (one paragraph under "Proof-search arena", renamed "Arenas")
- Create: `sylver/arena/data/league/REPORT.md`, `standings.json`, `plan.json`, `games.jsonl.gz`

CLI:

```text
python -m sylver.arena play FIRST SECOND --output DIR [--start 5,7] [--games 2]
       [--max-move 1000] [--cpu 2.0] [--increment 0.1] [--seed 0]
python -m sylver.arena league --output DIR [--players random,smallest,exact,book]
       [--external NAME=/abs/executable]... [--suites empty,enders,database]
       [--per-band 1] [--workers 4] [--max-move 1000] [--cpu 2.0] [--increment 0.1]
       [--seed 0] [--analyze-bound 0]
```

`play` alternates seats across `--games` (game 0: FIRST moves first; game 1: SECOND moves first) and prints each result line. Player names resolve to built-ins; anything containing `/` is an external absolute executable.

- [ ] **Step 1:** Add a CLI smoke test: `subprocess.run([sys.executable,'-m','sylver.arena','play','smallest','random','--start','4,5','--games','2','--output',str(d/'p')], check=True)` then assert two `record.json` files exist.
- [ ] **Step 2:** Implement; run `python -m unittest tests.arena.test_game -v` → PASS.
- [ ] **Step 3:** Record the pilot: `python -m sylver.arena league --output /tmp/league-pilot --players random,smallest,exact,book --suites empty,enders,database --per-band 1 --workers 4 --analyze-bound 150 --seed 0`; copy `REPORT.md`, `standings.json`, `plan.json` and `gzip -n` of `games.jsonl` into `sylver/arena/data/league/`. Add `sylver/arena/data/**/*.gz` is already marked generated in `.gitattributes`.
- [ ] **Step 4:** Documentation: the README section explains rules (cap semantics and the `{2,3}` end test), protocol, clocks and the session-accounting limitation, built-ins, league outputs, and the scope note. Include the commands above.
- [ ] **Step 5:** Full arena suite: `python -m unittest discover -s tests/arena -t .` — the new tests pass; pre-existing failures (sandbox/namespace-dependent) are unchanged and noted.
- [ ] **Step 6: Commit** — `git commit -m "Add play/league CLI, docs, and a recorded pilot league"`
