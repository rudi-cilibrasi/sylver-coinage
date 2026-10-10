# The search for an answer to 38

These are the working scripts and their outputs. They ran from one directory
holding all of them, `kunz` (`sylver/kunz_solver.cpp` at 0668ae4, built
with `-O3 -march=native -pthread`), and `known_p.json`.

`known_p.json` lists the known P-positions the search could answer into:
- the certified nodes of `sylver/short_certificates.py`;
- The Book's P targets, W, U, Y, Z and Z′;
- the published and pairing-family positions {8,10,22}, {8,12},
  {8,10,12,14}, {8,12,18,22} and {8,12,26,30};
- the gcd-two P facts of the arena's knowledge snapshot;
- the positions this search found P, as it found them.

The certificate's audit does not use this file.

| Step | Command | Output |
| --- | --- | --- |
| odd obligations of {16,38}'s 17 short even candidates | `THREADS=4 MAX_STATES=300000000 python odd_filter.py` | `odd_filter.jsonl` |
| the rest of 72's and 104's odd obligations | `kunz --threads 5 --stop-at-p --max-states 600000000 --odd-list 69,77,85 16 38 72` (and `85,93,101 16 38 104`) | `odd72.*`, `odd104.*` |
| {16,38}'s 11 odd candidates the o16 scan left | `kunz --threads 6 --stop-at-p --max-states 1400000000 --odd-list 71,69,77,79,85,93,101,87,109,117,125 16 38` | `odd_open.*` |
| the odd candidate 85 alone | `kunz --threads 4 --stop-at-p --max-states 1000000000 --memo-stats --odd-list 85 16 38` (stopped at the cap) | `odd85.*` |
| each of the seven open odd candidates alone (October 10) | `./odd_queue.sh`: `kunz --threads 8 --stop-at-p --max-states 1700000000 --memo-stats --odd-list M 16 38` per candidate | `odd_queue.*` |
| 109, 117 and 125 again, alone at 2.1 billion states | `./odd_retry.sh` (`--max-states 2100000000`) | `odd_retry.*` |
| even obligations of a candidate a | `python even_resolver.py A` | `even_A.jsonl` (A = 8, 24, 40, 56, 72, 88) |
| even obligations of any short position | `python resolve_position.py G...` (`--only-long` skips short children) | `resolve_<G>.jsonl` |
| even replies into short P-positions | `python pair_search.py G...` | `pair_*.log` |
| finite witnesses avoiding {8,10,22} | `python witness.py G...` | `witness_H.log` |
| each position's evidence, with sequential counts | `THREADS=2 python collect.py RESOLVED OVERRIDES G...` | `evidence_*.json` |
| certificates and replays | `python replay.py EVIDENCE PREFIX r38 NAME` | `../<prefix>*-certificate.json`, `../verification/` |
| even replies into short P-positions, from any gcd-two position | `python pair_search_any.py G...` | `pair_any_*.log` |
| deep odd witnesses, resuming after a resolver | `python deep_witness.py [--after N \| --done-count K] [--also W,...] G...` | `deep_*.log`, `deep_<G>.jsonl` |
| B56's evidence | `THREADS=3 python collect.py resolve_16-38-56-60.jsonl '{"74": [205, "finite"]}' 16 38 56 60` | `evidence_16-38-56-60.json` |
| B56's replays | `replay.py` on `evidence_B56_py.json` (Python), and with `REPLAY_PYTHON=0` on `evidence_B56_native_*.json`; then `python kunz_receipts.py MOVE...` | `../b56_*`, `../verification/b56_*/` |

Notes:
- The sweeps ran without `--verify-memo`. `collect.py` re-ran each
  certified position's odd obligations with `--verify-memo`, and the
  certificate replays every finite witness it uses.
- The resolvers search a long child's odd replies in increasing order of the
  destination's Frobenius number, in batches sharing one memo.
  - They first gave up on an obligation when a batch hit its state cap
    (300,000,000). `even_56`'s seven `open` rows are such give-ups, not
    refutations.
  - They now skip the reply in progress and go on, up to four skips.
    `resolve_16-20-22-24` and the restarted map of the long children
    (`resolve_16-38`, from its move 42 on) used that.
- `collect.py` was given overrides for I's moves 8 and 10 (finite
  witnesses 13 and 33 in place of {8,10,22}), B28's move 50 (45 in place of
  the node M) and B24's move 20 (22 into I). That override named I by its
  working name `A`; the evidence file was relabeled `I` by hand before the
  replays.
- `status.py` tabulates {16,38}'s obligations from these outputs.
- The map of the long children (`resolve_16-38`) continued on October 10
  from 148 to 250; `resolve_16-38.jsonl` and `resolve_16-38-long.log`
  grew by those fourteen rows (the log also ends with the map's summary).
- B56's evidence was first split at 100,000,000 states.
  - Below that, the witnesses were replayed natively and in Python
    (`evidence_B56_py.json`).
  - From there up, they were replayed natively and by `kunz_receipts.py`
    (`evidence_B56_native*.json`, `kunz_B56_*.log`): a sequential
    `kunz_solver.cpp` run with `--verify-memo`, whose source is kept in
    `../verification/sources/`.
  - Review then moved the three from 106 to 138 million states (42, 100,
    106) to native and Python replays (`evidence_B56_py2.json`,
    `replay_B56_py2.log`), as the Z record did up to 145 million.
  - Their earlier native and Kunz replays (`kunz_B56_b.log`) agreed, but
    the audit uses the Python ones. Only the four above 175 million states
    keep Kunz replays.
  - The Python replay of b56_30 first ran out of `replay.py`'s time budget,
    on a host whose load average was about 23. Its incomplete receipt was
    removed and the replay rerun with `REPLAY_RATE=3000`, a longer budget.
- Deep sweeps of candidate 72's long children are in `deep_72_*.log` and
  `deep_16-38-*.jsonl`. They found the winners 58 → 129 and 66 → 69. For
  68, 78 and 84 they found none before they were stopped.
- Some runs were stopped or still going when B56 was added:
  - the resolvers for 72 and 88;
  - the map of {16,38}'s long children;
  - `hard_queue.py`, which tests the replies the deep sweeps skipped, one
    at a time with a 1,000,000,000-state cap.

  Their files here are snapshots. `even_40` was stopped once B28 refuted 40.
- `collect.py` now names the nested positions I, B28, B24 and B56. These
  three evidence files did not use that table: B24's move 20 came from an
  override.
