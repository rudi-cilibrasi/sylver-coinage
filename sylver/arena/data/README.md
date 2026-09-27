# Recorded arena evidence

This directory records the first offline arena pilot, its regression
checks, the certificate golf pilot, and the game league pilot. None uses
network access or paid API calls; the first pilot's model arm is a scripted
test double. None claims a new mathematical discovery.

| Artifact | Contents |
| --- | --- |
| [pilot/REPORT.md](pilot/REPORT.md) | Training and held-out tables, three repetitions, failures, distributions, and the decision to revise before a live evolutionary campaign. |
| [pilot/summary.json](pilot/summary.json) | Counts, measured CPU, model usage, and per-target median comparisons. |
| `pilot/artifacts.tar.gz` | Full fixtures, predeclared plan, proposals, selection, certificates, transcripts, hashes, and CPU receipts. Compiled binaries are omitted. |
| [historical/summary.json](historical/summary.json) | Full B and W134 native replays, including certificate bytes, CPU, and state counts. |
| `historical/artifacts.tar.gz` | Historical adapter inputs, proofs, solver output, and accounting receipts. |
| [live/snapshot-manifest.json](live/snapshot-manifest.json) | Stable full post-PR5 database export: 308,280 facts, including the historical 305,011-row exact cache. |
| `live/w-*.json` and `live/knowledge/` | Six portable, hash-pinned historical W challenges sharing one compressed snapshot. Move 102 is public regression; 70,86,92,108,118 remain live. |
| `manifest.json` | SHA-256 digests for the published evidence files. |

The source profiles pin file contents, so committing these artifacts does
not change their identities. Live manifests record the machine and the arena
sources that produced them (the accounting and sandbox changes after this
pilot are a new execution profile). Generate new fixtures to rate episodes
under another machine's or source version's profile;
do not compare those scores directly with these measurements. Mathematical
re-verification can use another checkout of the pinned verifier.

## Certificate golf pilot (#16)

| Artifact | Contents |
| --- | --- |
| [golf/REPORT.md](golf/REPORT.md) | Median S per target and competitor, lowest-median counts, findings and decision, and every per-run leaderboard. |
| [golf/summary.json](golf/summary.json) | Per-target medians, winners, and the best certificate's C, T, and S. |
| [golf/plan.json](golf/plan.json) | Predeclared tiers, repetitions, seed, workers, pinned hint digest, targets, and competitors. |
| `golf/leaderboard-AB.json`, `golf/leaderboard-C.json` | Per-target rankings, grouped by identical task, snapshot, verifier, and execution profile. |
| `golf/artifacts.tar.gz` | Golf fixtures with the pinned hint file, and every episode's bundle, competitor, certificate, transcripts, and CPU receipts. Compiled binaries are omitted. |

The pinned hint file is `aa421ec0…` (308,322 facts: the 305,011-row cache
plus the post-PR13 evidence graph), inside the archive at
`fixtures/visible/hints/`. The Book seeded by this pilot is
[../book/BOOK.md](../book/BOOK.md). Replay any archived golf episode as
described above, passing the extracted episode directory to
`python -m sylver.arena verify`.

## Game league pilot (#17)

| Artifact | Contents |
| --- | --- |
| [league/REPORT.md](league/REPORT.md) | Standings, Bradley–Terry ratings with the prior-set gaps flagged, head to head, loss reasons, adjudicated openings, per-move CPU, and blunder analysis. |
| [league/standings.json](league/standings.json), [league/plan.json](league/plan.json) | Machine-readable standings; the predeclared plan with player commands, code digests, and the commit. |
| `league/games.jsonl.gz` | Every game: moves with per-move CPU and wall time, claims, results, and accounting method. |

Game results are games, not proofs; the league report re-renders exactly
from these files.

## Replay an archived pilot episode

Replays need the verifier version that produced the episode. Certificate
golf (#16) changed verifier sources, so replay the first pilot and the
historical checks from a checkout of commit `589066c`, for example
`git worktree add /tmp/pilot-checkout 589066c`, and run these commands
there. Golf episodes replay from the golf commit onward.

From the repository root, extract into a new directory:

```sh
mkdir /tmp/arena-evidence
tar -xzf sylver/arena/data/pilot/artifacts.tar.gz -C /tmp/arena-evidence
python -m sylver.arena verify \
  /tmp/arena-evidence/pilot/held-out/round-00-task-00-interleaved \
  --output /tmp/arena-evidence/replay
```

Every episode has its own `receipt.json` and canonical `certificate.json`.
Replay checks the artifact digests and recomputes mathematical validity and C.
It does not replace historical discovery/verification CPU or S. The archived
absolute command paths are historical metadata; replay rebuilds the native
tool from the current pinned checkout.

Run a fresh pilot with the same seed and repetitions:

```sh
python -m sylver.arena pilot --output /tmp/arena-pilot-new --repeats 3 --seed 0
```

CPU timings need not match. Recorded proposals and measurements reproduce
selection exactly; fresh measurements may select a different candidate. The
small public held-out panel is an engineering control, with acknowledged
prior-exposure risk. Development smoke runs preceded this final recorded run;
they are not additional independent trials in the reported distributions.

## Historical proof replays

B checks 69 finite leaves using one fresh memo, reaching 63,503,395 states.
W134 checks the reply-85 child P, reaching 37,192,385 states. These are full
native regression checks of existing results, with no new branch closure.
They are unranked: historical discovery cost is unknown. Their execution
metadata records an earlier development profile; the mathematical verifier
source hashes match this checkout. Their CPU costs are not tournament scores.

```sh
tar -xzf sylver/arena/data/historical/artifacts.tar.gz -C /tmp/arena-evidence
python -m sylver.arena verify-proof \
  /tmp/arena-evidence/historical/visible/public-b.json \
  /tmp/arena-evidence/historical/evaluator/public-b-reference.json \
  --output /tmp/arena-evidence/b-replay
python -m sylver.arena verify-proof \
  /tmp/arena-evidence/historical/visible/public-w134.json \
  /tmp/arena-evidence/historical/evaluator/public-w134-reference.json \
  --output /tmp/arena-evidence/w134-replay
```

These large checks use a 16 GiB memory cap and can take several minutes.
The original historical certificates and solvers have not been edited.

## Issue coverage

| Issue | Implementation and evidence |
| --- | --- |
| #7 | `snapshot.py`, `fixtures.py`, portable live bundles, stable repeated full export, conflict/dependency/hidden-label rejection tests. |
| #8 | `proof.py`, closed proof rules, canonical bytes, negative proof tests, full B/W134 replay receipts. |
| #9 | `supervisor.py`, `episode.py`, exact score, process-tree CPU, killed/orphaned/cancelled workers, resource failures, charged resume tests. |
| #10 | `protocol.py`, `policies.py`, `agent.py`, three baselines, isolated configurable providers, mock and usage-limit tests. |
| #11 | `evolution.py`, explicit prompt/policy seeds, training-only selection, bounded proposals/archive, failed candidates and generation overhead in the pilot. |
| #12 | CLI, per-target reports, 144 repeated tournament episodes, portable replay test from another source checkout, independently checked versioned admission. |

Live admission requires additional independent Python finite-leaf replay.
The admission integration test uses a small synthetic live target; no actual
W result was admitted by this pilot. W P would establish Q N, while U P still
also requires X N. Opening 16 remains unresolved.
