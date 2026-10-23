# The scan for finite answers

| Step | Command | Output |
| --- | --- | --- |
| odd answers to the replies 36–200 | `python finite_answers.py 36 200` | `finite_answers.jsonl` |
| each answer's destination alone, sequentially | `kunz --threads 1 16 R A` | `sequential_counts.txt` |
| certificates and native + Python replays | `python replay.py evidence_o16_py.json o o16 "{16}"` | `../o*-certificate.json`, `../verification/` |
| native replays of 62 and 86 | `REPLAY_PYTHON=0 python replay.py evidence_o16_native.json o o16 "{16}"` | `../verification/o62/`, `../verification/o86/` |
| sequential Kunz replays of 62 and 86 | `python kunz_receipts.py 62 86` | the same directories |
| the stopped sweeps again, with the P-table engine (October 14 and 18–20) | `python o16_scan2.py` (4 threads, an 8 GB cache: 42, then killed on 46), then `python o16_scan2.py --threads 10 --ncache-mb 16384 --timeout 2700`; `o16_watch.sh` waited for an answer | `o16_scan2.*` |
| six of those sweeps again, with a 3-hour limit each (October 22–23) | `python o16_scan3.py --threads 10 --ncache-mb 16384 --timeout 10800 68 76 84 92 100 42`; `o16_watch3.sh` waited for an answer | `o16_scan3.*` |

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

- `o16_scan2.py` resumed the 50 stopped sweeps besides 38's (which has its
  own campaign, `../../r38-2026-10-09`; 51 sweeps had stopped early), each at
  its candidate in progress and in the same order, with `kunz_pt`:
  `sylver/kunz_solver.cpp --p-table` at e335ff0, built like `kunz` (the
  reply-38 scan's build), whose `--max-states` counts P-positions
  (400,000,000 here). One P-table and N-cache served each reply's sweep, and
  each sweep had 45 minutes. 42 ran on October 14 from 18:07 with 4 threads
  and an 8 GB cache, sharing the host with the reply-38 hunt. At about 18:55
  Claude Code reclaimed memory and killed the run on 46 (which left no
  record), and it stayed paused for the reply-38 hunt. It resumed on October
  18 at 15:31 with 10 threads and a 16 GB cache for the other 49, until
  October 20 at 03:33. The script reads each sweep's rows as the engine
  prints them and writes one record per reply to `o16_scan2.jsonl` when the
  sweep ends, so a sweep the time limit stopped keeps what it classified, but
  a killed script loses its reply in progress.
- The rescan found no answer (by search; nothing here is replayed). All 49
  sweeps that ran timed out, and 198's again failed at once (Frobenius bound
  2039). They classified 114 more candidates, all N; eight of the timed-out
  sweeps (42, 98, 122, 154, 162, 178, 190 and 194) classified none.
- What the rescan left: the 35 gcd-2 replies have 17 to 195 candidates
  left each (all 25 above 94 have 80 or more), and some single candidates
  took over 45 minutes on 10 threads, so sweeping them all in order this way
  is out of reach. The 15 gcd-4 replies have fewer: 68 has 1 left, 76 has 2,
  84 has 4, 92 has 5 and 100 has 7; the ten from 108 to 196 have 9 to 32
  each.
- `o16_scan2.py`'s docstring says rows stream to `o16_scan2.jsonl`; they
  stream to the script, which writes the file as described above. The log
  calls 198's sweep "stopped": the script has no label for a failure, which
  its record shows (return code 1, and the engine's message).
- To run `o16_scan2.py` again: it calls `kunz_pt` at an absolute path in the
  session's scratch directory, it skips every reply already in
  `o16_scan2.jsonl` (so all of them, as committed), and the start, resume
  and done lines of `o16_scan2.log` came from the shell that launched it;
  `o16_watch.sh` waits for the done line or an answer in the jsonl.

- `o16_scan3.py` gave six of those sweeps longer runs: the five gcd-4
  replies with 1 to 7 candidates left, and 42, the lowest reply rescanned.
  It resumed each at the candidate the rescan stopped in (the ledger's
  `swept` plus the candidates `o16_scan2.jsonl` classified), in the same
  order, with the same engine and cap, on 10 threads with a 16 GB cache (42's
  first run with them: its rescan had 4 threads and an 8 GB cache), and a
  3-hour limit a reply, from October 22 at 22:03 to October 23 at 09:00.
- Round 3 found no answer (by search). It classified 20 more candidates,
  all N:
  - The sweeps for 68 and 76 finished. Every candidate for them is N: the
    odd gaps above 1 of {4,17} and {4,19} (15 for 68, 17 for 76), all legal
    after its reply. That still leaves both replies open, since a complete
    sweep tries only those gaps.
  - The other four stopped at the cap of 400,000,000 P-positions, none at
    the time limit. 84 stopped in 55 (55 and 59 left), 92 in its first
    candidate, 49 (49 to 65, five left), 100 in 51 (51 to 71, six left),
    and 42 in 123 (123, 131 and 139 left). On 10 threads, 42 went from
    none classified to 14.
  - The cap counts the P-positions in a sweep's shared memo, and the
    earlier candidates had used much of it: 42's sweep reached 123 with
    380,938,570 already held (95% of the cap), 100's reached 51 with
    297,542,575 (74%) and 84's reached 55 with 181,772,273 (45%). These are
    the last number in each record's last row, the engine's
    `cumulative_states`. Only 92's 49 had the whole cap.
- `o16_scan3.py`'s docstring repeats `o16_scan2.py`'s below "The earlier
  notes follow", with its usage line and its note that rows stream to
  `o16_scan2.jsonl`; `o16_scan3.py` writes `o16_scan3.jsonl`, one record
  per reply when its sweep ends. Each sweep `o16_scan3.log` calls "stopped"
  stopped at the cap (its record has `timed_out` false and the engine's
  message in `stderr_tail`); the script prints "stopped" for any early end
  that is neither a timeout nor an answer, a failure included. Here "done"
  means every candidate was classified (the script also prints it after an
  answer; this round found none). The start and done lines came from the
  shell that launched the script, and `o16_watch3.sh` waited for the done
  line or an answer.
- To run `o16_scan3.py` again: like `o16_scan2.py`, it calls `kunz_pt` at an
  absolute path in the session's scratch directory; it reads
  `o16_scan2.jsonl` from its own directory and skips every reply already in
  `o16_scan3.jsonl` (all six, as committed). With no replies named it takes
  every stopped reply in the ledger except 38, 198 included.

The scripts point at the main checkout (`/home/ruclaw/src/sylver-coinage`)
and the working directory they ran in.
