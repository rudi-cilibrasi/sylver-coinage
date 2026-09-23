# Recorded arena evidence

This directory records the first offline arena pilot and its regression
checks. The pilot uses a scripted model test double, no network, and no paid
API calls. No live mathematical discovery is claimed.

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
not change their identities. Live manifests record the machine that produced
them. Generate new fixtures to rate episodes under another machine's profile;
do not compare those scores directly with these measurements. Mathematical
re-verification can use another checkout of the pinned verifier.

## Replay an archived pilot episode

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
