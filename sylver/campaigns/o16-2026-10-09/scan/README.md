# The scan for finite answers

| Step | Command | Output |
| --- | --- | --- |
| odd answers to the replies 36–200 | `python finite_answers.py 36 200` | `finite_answers.jsonl` |
| each answer's destination alone, sequentially | `kunz --threads 1 16 R A` | `sequential_counts.txt` |
| certificates and native + Python replays | `python replay.py evidence_o16_py.json o o16 "{16}"` | `../o*-certificate.json`, `../verification/` |
| native replays of 62 and 86 | `REPLAY_PYTHON=0 python replay.py evidence_o16_native.json o o16 "{16}"` | `../verification/o62/`, `../verification/o86/` |
| sequential Kunz replays of 62 and 86 | `python kunz_receipts.py 62 86` | the same directories |
| the stopped sweeps again, with the P-table engine (October 14 and 18–20) | `python o16_scan2.py` (4 threads, an 8 GB cache, for 42), then `python o16_scan2.py --threads 10 --ncache-mb 16384 --timeout 2700`; `o16_watch.sh` waited for an answer | `o16_scan2.*` |

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

- `o16_scan2.py` resumed each of the 50 stopped sweeps but 38's (which has its
  own campaign, `../../r38-2026-10-09`) at the candidate in progress, in the
  same order, with `kunz_pt`: `sylver/kunz_solver.cpp --p-table` at e335ff0,
  built like `kunz` (the reply-38 scan's build), whose `--max-states` counts
  P-positions (400,000,000 here). One P-table and N-cache served each reply's
  sweep, and each sweep had 45 minutes. 42 ran on October 14 with 4 threads
  and an 8 GB cache; the run was then stopped for the reply-38 hunt, and
  resumed on October 18 at 15:31 with 10 threads and a 16 GB cache for the
  other 49, until October 20 at 03:33. Rows stream to `o16_scan2.jsonl` as
  the engine prints them, so a sweep the time limit stopped keeps what it
  classified.
- The rescan found no answer. All 49 sweeps that ran timed out, and 198's
  again failed at once (Frobenius bound 2039). They classified 114 more
  candidates, all N; 42, 98, 122, 154, 162, 178, 190 and 194 classified
  none. Many candidates left take over 45 minutes on 10 threads each, and
  most replies above 94 have 80 or more, so sweeping them all in order this
  way is out of reach.

The scripts point at the main checkout (`/home/ruclaw/src/sylver-coinage`)
and the working directory they ran in.
