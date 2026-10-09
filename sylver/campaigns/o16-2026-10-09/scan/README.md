# The scan for finite answers

| Step | Command | Output |
| --- | --- | --- |
| odd answers to the replies 36–200 | `python finite_answers.py 36 200` | `finite_answers.jsonl` |
| each answer's destination alone, sequentially | `kunz --threads 1 16 R A` | `sequential_counts.txt` |
| certificates and native + Python replays | `python replay.py evidence_o16_py.json o o16 "{16}"` | `../o*-certificate.json`, `../verification/` |
| native replays of 62 and 86 | `REPLAY_PYTHON=0 python replay.py evidence_o16_native.json o o16 "{16}"` | `../verification/o62/`, `../verification/o86/` |
| sequential Kunz replays of 62 and 86 | `python kunz_receipts.py 62 86` | the same directories |

`kunz` is `sylver/kunz_solver.cpp` built with `-O3 -march=native -pthread`.
The scan's sweeps ran on 8 threads without `--verify-memo`, stopping at the
first P or at an 800,000,000-state memo cap. Even a complete sweep tries only
the reduced pair's odd gaps, so a reply without an answer here is still open.
- A sweep with no answer and `swept` below `candidates` in
  `finite_answers.jsonl` stopped early: at the cap, or by failing partway.
  Without return codes the data cannot tell which. Either way the reply
  stays open.
- 198's sweep has `swept` 0. The engine rejected it: the candidate 685 gives
  {16,198,685}, with Frobenius number 2039, which needs a Kunz coordinate
  above its limit of 127 for modulus 16. The sweep's candidates share one
  memo, so none was classified. The script did not record return codes; it
  does now.

The scripts point at the main checkout (`/home/ruclaw/src/sylver-coinage`)
and the working directory they ran in.
