# The search for an answer to 28

These are the working scripts and their outputs, run from one directory
holding all of them, `kunz` (`sylver/kunz_solver.cpp` at c1eb16f, built
with `-O3 -march=native -pthread`), and `known_p.json`. `known_p.json` is the
repository's known P-positions: certified nodes, published positions, Book P
targets, W and U.

| Step | Command | Output |
| --- | --- | --- |
| odd obligations of each short candidate | `python odd_filter.py 22 142` | `odd_filter.jsonl` |
| even obligations of a candidate | `python even_resolver.py R` | `even_R.jsonl` (R = 38, 50, 58) |
| even replies for {16,28,38,40} | `python pair_search.py 16 28 38 40` | `pair_38_40.log` |
| Y's evidence, with each destination's sequential count | `python collect.py 58` | `evidence_58.json` |
| Y's certificates and native + Python replays | `python replay_y58.py` | `y58/`, copied to `../y*-certificate.json` and `../verification/` |
| deep sweep of {16,28,50,118} | see below | `deep50/` |

The deep sweep used the U record's driver, seeded with the replies up to 401
that the resolver had already swept:

```sh
python sylver/campaigns/u-2026-09-27/scan/sweep_w.py --out deep50 --parent 16,28,50 --move 118 \
    --binary-pattern kunz-c1eb16f --threads 8 --batch 800 --mem-gib 30 --rmax 1929 --verify \
    --extra-args "--max-states 900000000"
```

Only `deep50/` ran with `--verify-memo`; the other sweeps are search records,
and the certificate replays what it uses.
