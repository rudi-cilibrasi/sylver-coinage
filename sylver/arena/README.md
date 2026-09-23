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
Bubblewrap (`bwrap`) for external agent/provider commands. No network,
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
Supervisor CPU is charged too. `/proc` sampling enforces aggregate CPU/RSS
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
External ordinary programs or AI providers run in a Bubblewrap sandbox with
system runtimes and their explicit provider files; the checkout, home,
evaluator, referee, and baseline files are not mounted. Network access is off
unless the configured trusted provider explicitly requests it.

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
