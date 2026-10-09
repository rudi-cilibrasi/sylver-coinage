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
| even obligations of a candidate a | `python even_resolver.py A` | `even_A.jsonl` (A = 8, 24, 40, 56, 72, 88) |
| even obligations of any short position | `python resolve_position.py G...` (`--only-long` skips short children) | `resolve_<G>.jsonl` |
| even replies into short P-positions | `python pair_search.py G...` | `pair_*.log` |
| finite witnesses avoiding {8,10,22} | `python witness.py G...` | `witness_H.log` |
| each position's evidence, with sequential counts | `THREADS=2 python collect.py RESOLVED OVERRIDES G...` | `evidence_*.json` |
| certificates and replays | `python replay.py EVIDENCE PREFIX r38 NAME` | `../<prefix>*-certificate.json`, `../verification/` |

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
- Some runs were still going when this record was committed: the
  resolvers for 72 and 88, the one for {16,38,56,60}, and the map of
  {16,38}'s long children. Only the last is included, as the snapshot
  `resolve_16-38.jsonl`. `even_40` was stopped once B28 refuted 40.
- `collect.py` now names the nested positions I, B28, B24 and B56. These
  three evidence files did not use that table: B24's move 20 came from an
  override.
