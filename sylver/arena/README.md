# Verifiable proof-search arena

This CLI implements issues #6–#12: frozen knowledge, canonical proofs,
accounted episodes, ordinary/agent search policies, bounded evolution, and
per-target tournaments. It uses the existing exact evaluator and Quiet End
rule. Historical campaign files and their fingerprints are unchanged.

Run the offline pilot from the repository root:

```sh
python -m sylver.arena pilot --output /tmp/arena-pilot
```

It requires Python 3.11+, g++, Linux `/proc`/`wait4`/subreaper support, and
a sandbox for external agent/provider commands: Bubblewrap (`bwrap`) where
unprivileged user namespaces work, otherwise Landlock (Linux 5.13+, no
privileges needed; see below). No network,
credentials, Python packages, or paid model calls are needed. Output paths
must be new. The default pilot compares three baselines, a scripted agent,
and selected prompt/policy variants on four training and four held-out
fixtures, with three repetitions. `REPORT.md` includes every deployment,
coverage, score distributions, failed mutation candidates, and a decision.
The scripted model is a test double; this pilot is not evidence of real LLM
prompt-evolution performance.

## Frozen knowledge and tasks (#7)

A snapshot contains canonical P/N facts, provenance artifact hashes,
explicit fact dependencies, and permitted theorem IDs. Conflicting facts,
missing dependencies, cycles, and unknown theorem IDs are rejected. Its ID
is SHA-256 of its canonical JSON bytes. Starting facts are explicit
competition assumptions; exporting is not a new proof of the historical
305,011-row cache.

```sh
python -m sylver.arena fixtures --output /tmp/arena-fixtures --historical
python -m sylver.arena inspect /tmp/arena-fixtures/visible/training-4-5.json
python -m sylver.arena snapshot \
  --graph sylver/campaigns/w-seven-2026-09-22/deep/proof-graph.json \
  --output /tmp/post-pr5-snapshot.json
```

Every visible bundle contains one target, its kind/context, snapshot hash,
verifier profile, and execution profile. It cannot contain evaluator labels,
reference proofs, or arbitrary file/URL references. Large baselines can be
stored once as `knowledge/SHA256.json.gz`; loaders allow only that derived,
content-addressed location and verify the uncompressed canonical bytes.
Snapshot provenance does not require historical absolute paths.

The fixture curator keeps `evaluator/labels.json` and public reference
proofs separately. Only one designated bundle is passed into an episode.
External agents see that task through the protocol; neither the fixture
catalog nor evaluator directory is mounted in their sandbox. Training
selection accepts only training manifests. Held-out outcomes are evaluated
once at the predeclared post-selection checkpoint and never returned to the
proposer. The small fixtures and historical problems are public, so prior
model exposure remains a contamination risk even when local labels are hidden.

Generate the six historical post-PR5 W-child challenges with:

```sh
python -m sylver.arena fixtures --output /tmp/arena-live --live \
  --cpu-seconds 1800 --wall-seconds 3600 --memory-mb 16384
```

These use the full frozen post-PR5 database. Moves 70,86,92,108,118 are live;
102 is now **public regression**, because PR13 published reply 95. No hidden
reference solution is added to their visible baseline. The other public
regression fixtures include B and move 134. A target already labeled solved
in its visible snapshot is rejected, regardless of its fixture kind.

## Proof format and verifier (#8)

A schema-1 proof has `root` (a canonical comma-separated position key) and a
`nodes` map. Nodes use one of four closed rules:

| Rule | Fields beyond `rule`, `outcome` | Meaning |
| --- | --- | --- |
| `finite` | none | Recompute this gcd-one position. |
| `baseline` | `fact` | Reference an ID permitted by this exact snapshot. |
| `edge` | `move`, `child` | N, with a legal move to a proved P child. |
| `cover` | `tail`, `children` | P, with every required move going to a proved N child. |

Cover rows have `move` and `child`. A finite cover must enumerate **all**
legal moves other than poisoned move 1. A short gcd-two cover uses the fixed
`quiet-end-v1` rule, all even gaps and exceptional odd gaps, and an authorized
Quiet End theorem ID. Long positions have an explicitly unproved infinite
odd tail. An empty list or a finite odd prefix cannot certify such a position.
No arbitrary lemma, path, URL, or new assumed outcome is a proof rule.

Canonical bytes are UTF-8 JSON with sorted object keys, no whitespace,
canonical integer positions, sorted cover rows, and one copy of each
reachable proof node. Unreachable structurally valid nodes are discarded;
malformed/circular support is rejected. **C counts this entire new bundle,
including root, nodes, and baseline references.** A trailing file newline,
logs, prompts, timing receipts, and human comments are outside C. Metadata
cannot hold proof dependencies. Bounds: at most 128 generators, values at
most 4096, 10,000 nodes, and finite Frobenius number at most 1023.

Verification sorts new finite leaves by `(Frobenius, canonical key)` and uses
one fresh shared native memo (16 machine words), with no discovery memo or
inherited outcome cache. The source profile pins the fixed checker, helpers,
worker, exact runner, and solver sources. Discovery results remain provisional
until this independent stage succeeds. Adapters for PR4 B and PR5 move 134
leave the original certificate bytes unchanged.

```sh
python -m sylver.arena verify-proof \
  /tmp/arena-fixtures/visible/public-w134.json \
  /tmp/arena-fixtures/evaluator/public-w134-reference.json \
  --output /tmp/w134-arena-check
```

The default five-second fixtures are smoke budgets. Generate historical
fixtures with larger `--cpu-seconds`, `--wall-seconds`, and `--memory-mb`
for full replay. Standalone proof verification reports C and verification
CPU, but **no score**, because its discovery cost is unknown.

## Episodes and accounting (#9)

The score is exactly `S = (C + 100) * (T + 1)` and
`log_score = log(C + 100) + log1p(T)`, lower being better.
T is discovery plus verification **CPU seconds**, not elapsed time, states,
or a remote-compute estimate. Invalid, unsolved, interrupted, unmeasured, and
over-budget runs have null scores.

Each phase has a Linux subreaper supervisor. Final user+system CPU comes
from `wait4`: descendants reaped by their parents are included, and orphaned
children (including a new process session) are adopted, killed, and charged.
Supervisor CPU is charged too, so the supervisor tracks its process tree
incrementally: it reads `/proc` stat files only for tree members and for
pids it has not seen, and lists `/proc` to discover new processes every
50 ms. (Re-reading every stat file on each 10 ms poll cost about 20 ms of
charged CPU on a workstation running ~450 processes, rivaling the work being
measured.) Newly forked processes therefore enter aggregate RSS/CPU
sampling within 50 ms; every decision that nothing remains to kill or charge
uses a full rescan. `/proc` sampling enforces aggregate CPU/RSS
and a wall watchdog; per-process address-space/CPU limits provide additional
hard guards. Aggregate polling has scheduler-sized overshoot; final measured
CPU above the episode budget invalidates the score. Memory is a per-process
address-space cap plus a sampled aggregate RSS cap, not a cgroup reservation.

Compilation and immutable fixture preparation happen before episodes.
Policy/agent initialization, routing, failed queries, local provider commands,
all solver workers, and verification are charged. Both phases draw from one
CPU/wall budget. Hardware, kernel, Python/libc/compiler versions, local source
hashes, model ID, and limits identify the execution profile. Providers report
remote requests, tokens, latency, and monetary cost separately; remote CPU
is never invented or multiplied into the score. Remaining quotas are sent
to providers before each call; over-reported-budget or unknown usage cannot
produce a rated win. A trusted provider wrapper must enforce its API's
per-request spending/token bounds before issuing a paid request.

```sh
python -m sylver.arena run /tmp/arena-fixtures/visible/training-4-5.json \
  --policy interleaved --output /tmp/arena-episode
python -m sylver.arena verify /tmp/arena-episode --output /tmp/arena-replay
python -m sylver.arena resume /tmp/interrupted-deterministic-episode
```

`verify` works after copying the artifact directory to another checkout of
the pinned verifier. It replays mathematical validity and C; it never replaces
historical discovery CPU or awards a cheaper historical score.

Deterministic resume retains every measured attempt, subtracts prior CPU and
active-worker wall time, and carries only the episode's discoveries forward.
An episode lock prevents concurrent writers. A missing final accounting
receipt refuses resume. Valid/invalid/over-budget episodes are sealed. Model
episodes are also sealed, so a continuation cannot reset provider quotas.
An interrupted process with no final CPU accounting stays unrated.

## Protocol, policies, and providers (#10)

The local JSONL protocol accepts `{ "id": ..., "op": ..., "args": ... }` and
returns `{ "schema": 1, "id": ..., "result": ... }`. Operations are `inspect`,
`lookup`, `profile`, `route`, `close`, `exact`, `proof`, `submit`, and `budget`.
`exact` accepts `positions` and a batch lifetime `seconds`; interrupted and
unsupported queries return `unknown`. Only complete, flushed solver rows
enter the episode's knowledge. `submit` returns
`awaiting-independent-replay`, never a win. All requests/responses are logged.

`python -m sylver.arena serve BUNDLE --output NEW_DIR` provides accounted
interactive exploration. Its stdout is JSONL and its resource receipt is
saved under `accounting/`. It has no tournament score. Rated external programs
use `run --agent CONFIG.json` so their local CPU is included as well.

The three built-ins use that same protocol:

- `increasing`: smallest finite bounds first, one query at a time.
- `interleaved`: shared-memo batches, rotating queues, deferring only the first
  unfinished request after interruption.
- `routes-short`: known P routing and supported short subsidiary covers before
  finite witness search.

Evolvable policy programs are a bounded JSON DSL: strategy, batch size, odd
limit, slice lifetime, rounds, subsidiary depth, and compact/witness proof
style. Competitors cannot execute arbitrary Python or replace the checker.
External ordinary programs or AI providers run sandboxed with system runtimes
(`/usr`, `/lib`, `/lib64`, `/bin`) and their explicit provider files (every
file named in the configured command); the checkout, home, evaluator,
referee, and baseline files are unreadable. Network access is off unless the
configured trusted provider explicitly requests it. `sandbox.py` chooses the
backend, recorded in each provider directory and in the execution profile:

- **Bubblewrap** when it can create namespaces: unmounted files are
  invisible, with private PID, IPC, and network namespaces and `/tmp`.
- **Landlock** otherwise, as on Ubuntu 24.04, whose AppArmor policy
  (`kernel.apparmor_restrict_unprivileged_userns=1`) blocks unprivileged user
  namespaces and hence every bwrap mode. A launcher restricts itself and then
  execs the provider: file contents and directory listings outside the
  allowed set are denied, writes go only to a fresh scratch directory
  (`TMPDIR`, `HOME`), TCP is denied, signals and abstract Unix sockets cannot
  leave the sandbox (Landlock ABI 6+), and a seccomp filter denies
  `socket()` (all families without network; `AF_UNIX` always, so a provider
  cannot ask a session bus or other local service to act for it), io_uring,
  and `ptrace`, `process_vm_readv`/`writev` and `pidfd_getfd`, so the
  same-user evaluator cannot be inspected whatever `kernel.yama.ptrace_scope`
  says. Two stated differences from bwrap: path existence and metadata
  (`stat`) remain visible, and there is no private PID namespace (other
  processes' `/proc` entries exist but cannot be read).

Automatic selection uses Landlock only from ABI 6 (Linux 6.12+), where
signals and abstract sockets are scoped; otherwise provider commands fail
closed with an explanatory error. `SYLVER_ARENA_SANDBOX=bwrap|landlock`
pins a backend (pinned Landlock accepts older ABIs and their weaker signal
isolation). The backend and ABI are part of the execution profile, so set
the variable identically when generating and running fixtures.

An agent config specifies an absolute executable/script command, a prompt or
prompt-template name, `model_id`, and request/token/cost/latency limits. Its
model ID and quotas must match the challenge profile. On stdin the provider
receives the prompt, visible task, seed, previous tool feedback, and remaining
model budget. On stdout it returns one JSON envelope:

```json
{"action":{"id":1,"op":"close","args":{"position":[4,6]}},
 "usage":{"input_tokens":120,"output_tokens":30,"cost":0.0}}
```

Prompts, responses, tool calls, seeds, and policy/configuration bytes are
retained. Credential environment values are passed selectively, excluded
from manifests, and redacted if echoed in provider output. Never put secrets
in command arguments or prompts. The bundled `mock_provider.py` is an offline
script with synthetic reported tokens, not a real model or tokenizer.

## Evolution and tournament (#11, #12)

```sh
python -m sylver.arena tournament /tmp/arena-fixtures/visible/training-*.json \
  --output /tmp/arena-tournament --repeats 3 --seed 0
python -m sylver.arena report /tmp/arena-tournament
python -m sylver.arena evolve /tmp/arena-fixtures/visible/training-*.json \
  --output /tmp/arena-evolution --candidates 9 --cpu-budget 120
```

`evolve --agent-template FILE` enables prompt seeds/variants under a compatible
model profile; `--proposer FILE --model-requests N --model-tokens N
--model-cost N` supplies a configurable mutation provider. Its envelope has
`candidate`, `rationale`, and `usage`, instead of a tool action. Without one,
a deterministic mock proposer exercises both accepted and rejected mutations.

The population starts from three policies and, when an agent template is
provided, two explicit prompt seeds. Selection uses **only training** mean
log(S), equivalent to a geometric mean. Any invalid/unsolved panel case has
infinite fitness (serialized as null). A bounded archive retains distinct
successful executable approaches. Lineage, proposals, rationale, failures,
all evaluation receipts, generation CPU/model overhead, and caps are saved.
Recorded proposals and measurements reproduce selection exactly; fresh timing
measurements and remote-model responses need not reproduce fitness exactly.

Leaderboards never mix targets, knowledge, verifier versions, or execution
profiles. They show validity/outcome, C, both CPU components, T, S, log_score,
min/median/max/stddev across repeats, and separate solved-target coverage.
No target weights or cross-target raw-score totals are introduced.

A live discovery is admitted only by a curator operation:

```sh
python -m sylver.arena admit LIVE_EPISODE --output /tmp/new-knowledge-version
```

This re-verifies the original artifacts, performs an additional independent
Python replay of all new finite leaves, then writes a **new** snapshot with
explicit proof/replay dependencies. Existing tournament snapshots and scores
are never updated in place. The additional admission checks are separate from
the episode's fixed verification profile and score.

Resolving W would establish Q N. U P still also requires X N; neither local
leaderboard improvements nor the current W results solve opening 16.

## Certificate golf and The Book (#16)

Golf asks a different question from discovery: given a result the database
already knows, how cheaply can a program **certify** it? Every golf target is
public (its outcome is in the manifest context), so golf measures
certification efficiency, never discovery, and the score is the same
`S=(C+100)*(T+1)`.

```sh
python -m sylver.arena fixtures --golf --output /tmp/golf-fixtures       # tiers A,B
python -m sylver.arena run /tmp/golf-fixtures/visible/golf-A-...json \
    --policy golf-probe --output /tmp/golf-episode
python -m sylver.arena golf-pilot --output /tmp/golf-pilot --workers 3   # tournament + Book
python -m sylver.arena book verify                                       # replay The Book
```

**Hints.** The frozen database (the 305,011-row cache plus the post-PR13
evidence graph, 308,322 facts) is an untrusted oracle. It is a sorted text
file, `hints/SHA256.txt.gz` beside the bundles, whose digest is pinned by
every golf manifest (only `golf` manifests may pin hints). The protocol's
`hint` operation returns `P`, `N`, or `unknown` for up to 4096 positions,
labelled `untrusted-hint`; the file loads on first use and that CPU is
charged. Hints never become proof nodes and no rule can cite them, so a
wrong hint can only make a certificate fail the fixed verifier's replay.
Golf bundles have an empty trusted snapshot: every byte of a certificate
counts in `C` and every finite leaf is replayed in `T`.

**Strategies** (policy DSL, no arbitrary code): `golf-root` submits one
finite leaf; `golf-witness` answers an N target with the hinted finite P
child of fewest gaps; `golf-probe`, when there is a choice, races bounded
exact queries (charged) over up to `batch_size` hinted witnesses and the
root, each capped by the time that could still beat the best estimate
`(C+100)*(seconds+1)`, and never falls back to a witness its probe refuted.
`golf-blind` is the hint-free control: it computes a finite target's outcome
exactly and searches up to `rounds` odd replies for a gcd-two target's
witness. A gcd-two N target has no finite root, so every strategy answers it
with a witness, scanning odd replies up to `odd_limit`. Finite P targets get
a root leaf, since a one-level cover multiplies `C` by roughly 50–100;
gcd-two P targets need covers, which these strategies do not build.
External programs and agents can build any certificate the proof language
allows, including covers.

**Panel.** Tiers A (Frobenius 100–150) and B (150–200) are predeclared,
seeded draws from the database, accepted by the verifier's deterministic
root-search state count rather than by timing. N targets are drawn among
positions with at least one hinted P child: the database records outcomes,
not winning moves, so only there does it create a choice. P targets are
root-leaf controls. Tier C is the campaign's own branch refutations
around W: moves 134 and 102 (gcd two, answered by 85 and 95) and the finite
pair after 102 and 89, whose verifier root search takes 6,382,154 states
against 1,721,485 for the hinted witness 33. Tier C needs a 16 GiB profile.

**The Book** (`sylver/arena/book/`) keeps, for each target, every admitted
certificate. `book add EPISODE` re-verifies it from scratch (never trusting
the episode's receipt) and records `C`, the verifier's evaluated-state count,
which must agree across runs, and each run's CPU. The entry of record
minimizes the deterministic checking cost `(C+100)*(states/RATE+1)`, the
agreed score's shape with verification time replaced by the verifier's own
work at a fixed `RATE` (100,000 states per second, recorded in the index), so
timing noise never changes the record; measured CPU is shown for
information. Entries are compared only under one verifier version. Book
entries are independent, cheaper-to-check certificates of public results,
not new mathematics. `book verify` replays every entry and requires the same
certificate digest, root, `C`, and state count; `book render` writes
`BOOK.md`.

### The Book of W

`W={16,26,62,98}` is the node of the move-26 program whose P outcome would
establish `Q={16,26,88,98}` N. `python -m sylver.arena book-w --output DIR`
certifies W's covered obligations into The Book and writes
[`book/W.md`](book/W.md), a table of all 52 obligations: certified by a
self-contained Book certificate, depending on a named infinite P position,
or open.

- Obligations whose recorded refutation is finite (an odd reply reaching a
  finite P position, or an odd move whose position is finite) are golf
  targets; the golf strategies certify them and every distinct valid
  certificate is admitted.
- `ShortProver` builds cover/edge/finite certificates for short gcd-two P
  positions and their N parents from hints, with a bounded exact-query
  fallback. It certifies `{4,6}` with a 191-byte Quiet End cover, so moves 4
  and 6 need no published position.
- `--certificates DIR` admits proof files from a longer curator search, each
  only after the Book's own replay. A search of odd replies found finite
  witnesses where the campaign had routed through theorem-backed positions:
  8 by 49, 10 by 9, 14 by 23, and 24 by 15 (instead of G, K, and `{12,14,16}`,
  whose certificates rest on Sicherman's `{8,10,22}` periodicity result and
  Blok's pairing family), and 20 by 14, reaching `R={14,16,20,26}`, whose
  Quiet End cover needs only finite witnesses and `{4,6}`.
- `--exclude` leaves out moves whose leaves are too large to replay alongside
  other work (the arena verifier holds each state in 16 words).

## Game arena

Programs also play Sylver Coinage against each other under CPU clocks.
**A game result is never a proof:** no win, rating, or win rate establishes
the outcome of any position. Nothing here changes the proof referee, the
episode accountant, or any file pinned by a recorded profile.

> **Players run sandboxed by default.** Each player runs under the arena's
> sandbox launcher (`sandbox.py`: Bubblewrap, or Landlock plus seccomp where
> user namespaces are unavailable) with a minimal environment. It can read only
> its own files (built-ins: the checkout, the interpreter, and the solver) and
> write only a scratch directory, and it cannot read other processes' `/proc`
> entries, signal or trace them, or leave its cgroup. A hostile player could
> otherwise write into its opponent's stdout pipe through `/proc/PID/fd/1`
> and have the referee record the opponent naming 1; a regression test runs
> exactly that attack and checks it fails. `--no-sandbox` restores unsandboxed
> play for trusted local programs, and reports then carry an isolation
> warning.

```sh
python -m sylver.arena play exact book --start 5,7 --games 2 --output /tmp/game
python -m sylver.arena league --output /tmp/league-pilot \
  --players random,smallest,exact,book --suites empty,enders,database \
  --per-band 1 --workers 4 --seed 0
```

`play FIRST SECOND` alternates seats (game 0: FIRST moves first) and prints
one JSON result line per game; names containing `/` are external absolute
executables. `league` also takes `--external NAME=/abs/executable` (repeatable),
`--max-move`, `--cpu`, `--increment`, and `--analyze-bound`. Output paths
must be new.

### Rules and the move cap

Players alternately name positive integers that are not sums of numbers
already named; whoever names 1 loses. A game may start from any position.
Every game records a cap `max_move = M >= 3` (default 1000): moves must lie in
`1..M`. For a gcd-one position whose Frobenius number is at most M, capped
play is exactly Sylver Coinage; otherwise the cap is a house rule and reports
call the game *capped*. The cap never ends a game early: a semigroup holding
every integer in `[2, M]` holds 2 and 3, hence every integer above 1. So the
game is over, and the player to move must name 1, **exactly when 2 and 3 are
both in the semigroup**, and the referee's state is one `(M+1)`-bit
membership set (`game.py`).

### Protocol (schema 1)

JSON Lines over stdin/stdout, one fresh process per player per game:

```text
-> {"type":"hello","schema":1,"rules":{"max_move":M},"seat":"first"|"second","clock":{...}}
<- {"type":"ready","name":"...","version":"..."}
-> {"type":"move","schema":1,"game":ID,"start":[...],"history":[...],"generators":[...],
    "gcd":d,"seat":"first","ply":k,"rules":{"max_move":M},
    "clock":{"cpu_remaining":x,"cpu_increment":y,"opponent_cpu_remaining":z}}
<- {"move":n,"claim":"win"|"loss"|"unknown","note":"<=200 chars"}    (claim, note optional)
-> {"type":"end","winner":"first"|"second","reason":"..."}
```

`generators` are the canonical minimal generators of the current semigroup;
`history` is every number named since `start`. Stdout carries protocol lines
only; players log to stderr, whose last 64 KiB the referee keeps. Claims are
recorded, never trusted. Player text (ready name and version, notes) is
stored as valid UTF-8, with unencodable characters such as lone surrogates
replaced by `?`, and truncated.

### Clocks, accounting, and losses

Each player has `cpu_base` seconds of CPU (default 2.0) plus a Fischer
increment (0.1 s) credited after each legal move. Where cgroup v2 is
delegated to this user (as in a systemd user session), each player runs in
its own child cgroup of the referee's: a tiny shell wrapper moves itself into
the cgroup and then execs the player, so every descendant starts inside it.
The clock is then the cgroup's cumulative `cpu.stat` usage, which keeps the
CPU of every descendant however it ends (reaped, auto-reaped because
SIGCHLD is ignored, orphaned, or in a new session), and `cgroup.kill` ends
them all at game end. Otherwise the referee falls back to summing
`utime+stime+cutime+cstime` from `/proc` over the live members of the
player's session, which misses children that no member reaps (SIGCHLD
ignored, double-fork orphans reaped by init) and processes that leave the
session, which it cannot kill either. Each game record says which method
each seat used (`accounting`). Either way, CPU spent after replying or
during the opponent's turn is charged at the player's next measurement, and
the clock is enforced while waiting, so a busy player loses on time at once.
Each move also has a wall-time safety limit of `3 x cpu_remaining + 5`
seconds. Setup (process start and the hello/ready handshake, such as loading
a database) is capped separately (10 s CPU, 60 s wall) and not charged to the
clock. Players run with a 4 GiB address-space limit (`memory_mb`); at game
end the referee kills the cgroup, then kills session members until none is
left alive, and reaps the player.

A player loses by naming 1 (`named-1`), naming a non-gap or out-of-range
number (`illegal-move`), replying without an integer move (`malformed-move`),
exceeding its CPU clock (`cpu-time`) or the wall limit (`wall-time`), exiting
or closing its pipes (`crashed`), or failing setup (`setup-failed`,
`setup-cpu`). When a move puts 2 and 3 in the semigroup, its maker wins
(`opponent-must-name-1`). An exception in the referee voids the game; void
games are listed and excluded from ratings.

**Limitations.** Without the sandbox (`--no-sandbox`), a same-user process
can move itself out of its cgroup (by writing its pid to an ancestor's
`cgroup.procs`) and so escape both the clock and the final kill, and under
the `/proc` fallback the escapes described above apply; such runs are for
trusted programs only. Sandboxed players cannot write cgroup files. Under the
Landlock backend, path existence and metadata stay visible (see the sandbox
section above).

### Built-in players

`python -m sylver.arena.players NAME [--seed S] [--options JSON]` speaks the
same protocol as an external program and is deterministic given its seed,
except that the exact players stop searching when their budget ends.

| Player | Behaviour |
| --- | --- |
| `random` | Uniform legal move. |
| `smallest` | Smallest legal move (a weak control). |
| `exact` | For a gcd-one position with Frobenius number at most `exact_bound` (180 with the native solver, 60 in Python) and the cap: an exact solve using up to a quarter of its remaining clock; plays a winning move, or, when lost, *complicates*. Otherwise it solves the finite children with small Frobenius numbers in increasing order and plays the first P child found, else complicates: of 16 seeded samples and the largest legal move, the one whose child is infinite, else has the largest Frobenius number. |
| `book` | `exact`, preceded by an outcome book: the 305,011-row exact cache plus cited P-positions (Hutchings primes, `{4,6}`, Blok, Sicherman, published and certified campaign positions). It plays the smallest legal move to a known P child at once; from the empty position it names 5. |

Book facts and claims describe the uncapped game; in capped games they are
heuristics only. The native solver is built once, like the proof arena's
shared tools, and passed to `exact` and `book` as an option.

### Leagues and reports

A league plays every opening with every ordered pair of distinct players, so
each pair meets in both seats, in parallel worker processes (default 4).
Opening suites: `empty` (the real game, capped), `enders` (small coprime
pairs, verified N), `database` (exact cache rows sampled reproducibly from
the Frobenius bands 0–60, 60–100, 100–140, and 140–180, with `--per-band`
P and N rows each), and `research` (`{16}`, `{16,26}`, W, X; exhibition only,
outcomes unknown). Outputs:

- `plan.json`: players with command, option, and solver-binary digests,
  openings, rules, clock, seed, the full schedule, the expected CPU
  accounting, and digests of the code and data that decide games (with the
  git commit, when available), written before the first game;
- `games.jsonl`: one complete record per game (moves with per-move CPU,
  wall time, and claims; setup costs; result, reason, and detail; CPU
  accounting per seat), appended as each game finishes, so an interrupted
  league keeps its completed games (games cut short are not logged);
  `games/ID/` also keeps each record and both players' stderr. All players
  of a league run under one cgroup of its own, which is killed and removed
  when the league ends, however it ends;
- `standings.json` and `REPORT.md`: scores, Bradley–Terry ratings on the Elo
  scale with bootstrap intervals (when the win graph is not strongly
  connected, Ford's condition fails: the report groups the players, says
  that gaps between groups are set by the prior, and gives intervals only
  for differences within a group), head-to-head results, loss reasons, how
  often the perfect-play winner won each opening with a known outcome, CPU
  per move, void games, and the reproduction command.

`--analyze-bound F` solves every reached position with gcd one and Frobenius
number at most F natively (60 s and 4 GiB each, unknown beyond) and counts
*blunders*, moves from an N-position to an N-position, per player. Analysis
CPU is reported separately and never changes a result. Database positions
above Frobenius number about 100 can each take a minute to solve, so keep F
modest.

The recorded pilot in [data/league/](data/league/REPORT.md) (`REPORT.md`,
`standings.json`, `plan.json`, and `games.jsonl.gz`) is a league of the four
built-ins over the `empty`, `enders`, and `database` suites with
`--analyze-bound 150`, run with the command in its report. It is an
engineering pilot: it measures the harness and the built-in players, not the
mathematics of any open position. CPU-clocked games depend on the machine and
its load, so a rerun need not reproduce every game.

## Checks and recorded evidence

```sh
python -m unittest discover -s tests/arena -q
```

Tests cover canonicalization against the reference semigroup implementation,
proof rejection, historical adapters, isolated providers, credential echoes,
CPU accounting, killed descendants, bounded queries, false submissions,
resume, model/proposer mocks, training-only selection, portable bundles,
re-verification from another source checkout, and versioned admission.
See `data/` for the recorded pilot and historical replay receipts.
