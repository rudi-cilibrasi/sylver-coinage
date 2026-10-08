# The search for an answer to 30

These are the working scripts and their outputs. They were run from one
directory holding all of them, `kunz` (`sylver/kunz_solver.cpp` at c1eb16f,
built with `-O3 -march=native -pthread`), and `known_p.json`, the known
P-positions the search could answer into (the certified nodes of
`sylver/short_certificates.py`, The Book's P targets, W and U). Only
`kunz_receipts.py` and the verification replays bear on the certificate; the
search sweeps ran without `--verify-memo`.

| Step | Command | Output |
| --- | --- | --- |
| {16,30}'s 27 odd obligations, with `--verify-memo` | the command at the top of the output | `odd_30.txt` |
| odd obligations of 30's 17 short even candidates | `python odd_filter.py` | `odd_filter.jsonl` |
| even obligations of a candidate e | `python even_resolver.py E` | `even_E.jsonl` (E = 4, 12, 14, 20, 24, 44, 50, 56, 104) |
| even obligations of any short position | `python resolve_position.py 16 30 44 56`, `... 16 30 40 44` | `resolve_*.jsonl` |
| odd witnesses instead of nodes K, O, S | `python avoid_h.py` | `avoid_h.json` |
| every odd answer up to 601 to Z+70, Z+130, Z+66 | `python alt_witness.py 70 130 66` | `alt_witness.json` |
| each position's evidence, with sequential counts | `python collect.py FILE OVERRIDES GENERATORS` | `evidence_*.json` |
| certificates and replays | `python replay.py EVIDENCE PREFIX OUTDIR NAME` | `../z*-`, `../zp*-certificate.json`, `../verification/` |
| sequential Kunz replays of 70→311, 130→225 | `python kunz_receipts.py 70 130` | `../verification/z70/`, `../verification/z130/` |

Two of the evidence files were edited after `collect.py`, swapping node
routes for finite witnesses (`avoid_h.json`): Z′'s moves 10, 20, 24 and 34, and
Z's move 10. In `evidence_16-30-56.json`, Z's move 44 is recorded as the reply
40 into "C30", the working name of Z′.
