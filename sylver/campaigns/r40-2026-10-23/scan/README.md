# The search for an answer to 40

These are the working scripts and their outputs. They ran from one directory
holding all of them and two builds of `sylver/kunz_solver.cpp`, the same ones
the [reply-38 search](../../r38-2026-10-09/scan/README.md) used:
- `kunz`, from 0668ae4;
- `kunz_pt`, from e335ff0, run with `--p-table`. Its state cap then counts
  P-positions.

Both were built with `g++ -std=c++20 -O3 -march=native -pthread`. The scripts
read the reply-38 search's `known_p.json` and add to it the finite
P-positions of the opening-16 table and ledger, {16,31,150} (search), and
{16,38,72} (search). After Q={16,20,46} was found P (October 23, 15:51),
`screen.py` added Q too. The known stage in `screen.jsonl` ran before that.

Except where the audit checks it, everything here is discovery output, not
certified.

| Step | Command | Output |
| --- | --- | --- |
| even candidates a = 2 mod 4 up to 398: an obligation reaching a known P-position | `python screen.py --amax 398` (October 23) | `screen.jsonl` (`known` rows) |
| the odd obligations of the survivors up to 62 | `python screen.py --odd --amax 62 --threads 2 --max-states 50000000 --timeout 300` (`kunz`) | `screen.jsonl` (the first `odd` rows, without engine fields) |
| again from 46, longer: pass A | `python screen.py --odd --p-table --ncache-mb 8192 --threads 10 --max-states 100000000 --timeout 1800 --amin 46 --amax 198 --redo-partial`, from 10:06; `./stop_after.sh PID 86` stopped it at 13:05, after 86 (the log's "done" line is the shell's, written when the watcher stopped it) | `screen.log`, `screen.jsonl` (the latest `odd` row per candidate counts) |
| 46's even obligations | `./even_triage.sh` (`even_resolver.py 46 --p-table --ncache-mb 8192 --threads 10 --max-states 100000000 --timeout 300`), 13:06 to 15:51; `./stop_on.sh PID even_triage.log 'even triage 46 end'` stopped it as 54 began | `even_triage.log`, `even_46.jsonl`, the first 17 rows of `even_54.jsonl` |
| even replies from 46's two short children whose odd obligations are all N | `./pair_queue.sh` (`pair_search_any.py C --p-table --ncache-mb 8192 --threads 10 --max-states 150000000 --timeout 600`) | `pair_any_16-20-46.log`, `pair_any_16-40-46-60.log` |
| Q's odd obligations | `kunz_pt --p-table --ncache-mb 8192 --threads 10 --max-states 150000000 --odd-list 3,5,7,9,11,13,15,17,19,21,25,27,29,35,37,45 16 20 46` | `odd_16-20-46.out`, `.err` |
| Q's even obligations | `python even_resolver.py --position 16 20 46 --p-table --ncache-mb 8192 --threads 10 --max-states 150000000 --timeout 600` | `resolve_16-20-46.jsonl`, `.log` |
| a finite reply to Q's child {16,20,22,46}, in place of a route through I={16,20,22,24} | `./small_sweeps.sh` (`kunz --threads 2 --stop-at-p --max-states 30000000 --odd-list W 16 20 22 46`, W the odd w up to 201 in the resolver's order, `w22.txt`) | `odd_16-20-22-46.out`, `.err` |
| the odd obligations of {16,40,30} and {16,40,38} | `./small_sweeps.sh` (`kunz --threads 2 --stop-at-p --max-states 60000000`) | `odd_16-40-30.*`, `odd_16-40-38.*` |
| finite replies for Q's moves 8, 24, 26 and 30, in place of the nodes G, K and O | `./q_finite.sh` (`kunz --threads 2 --stop-at-p --max-states 100000000`, odd w up to 201 in the resolver's order): 24 is answered by 29; 8, 26 and 30 have none | `q_finite_<move>.out`, `.err` |
| Q's evidence, each finite destination solved alone | `THREADS=2 python collect.py resolve_16-20-46.jsonl '{"22": [45, "finite"], "24": [29, "finite"]}' 16 20 46` | `collect_Q.log`, `evidence_16-20-46.json` |
| the finite refutations of answers to 40 | `python refutations.py 10:9 18:5 26:11 30:17 42:23 50:11 70:37 62:61`; again without `62:61`, whose destination took 286,533,125 states; after review with `2:3` first; and on October 25 with `94:21 102:33` added, from the light sweep below | `refutations_with_62.log`, `refutations_without_62.log`, `refutations.log` (the run after review), `refutations3.log` (the last run), `evidence_16-40.json` |
| certificates and replays | `REPLAY_MAX_JOBS=2 REPLAY_BUDGET_GIB=8 python replay.py evidence_16-20-46.json q DIR Q`, and `REPLAY_BUDGET_GIB=10 ... evidence_16-40.json r40_ DIR '{16,40}'` (DIR the record's directory), run again after each new evidence file. `replay.py` skips a receipt already verified, so `replay_Q.log` shows only the last run (q24, at 16:07); the per-job logs give the times of the others (16:00 to 16:03) | `replay_Q.log`, `replay_r40.log`, `replay_r40_2.log`, `../q*-certificate.json`, `../r40_*-certificate.json`, `../verification/` (each job's log, which `replay.py` writes beside the certificates, was moved there) |
| 54's even obligations, short children first | `./short_first.sh` (`even_resolver.py 54 --short-first --p-table --ncache-mb 8192 --threads 10 --max-states 100000000 --timeout 300`), from 15:53; `./stop_on.sh PID even_triage.log 'r=54 e=  92'` stopped it after its last short child, and with it the script's loop, so `run58.sh` ran 58 later | `even_triage.log`, `even_54.jsonl` |
| is a short child of 54, with every odd obligation N, itself P? | `./test_children.sh 54 52 60 68 76` (`even_resolver.py --position 16 40 54 E --short-first`, same settings), from 16:05; stopped by hand at 16:28, once {16,40,52,54} was P | `test_children.log`, `resolve_16-40-52-54.jsonl`, `resolve_16-40-54-60.jsonl` (partial) |
| a finite reply for B54's move 24, in place of the node K | `kunz --threads 8 --stop-at-p --max-states 100000000 --odd-list W 16 40 52 54 24` (W as above): none | `b54_finite_24.out`, `.err` |
| B54's evidence | `THREADS=8 python collect.py resolve_16-40-52-54.jsonl '{"36": [21, "finite"], "26": [11, "finite"]}' 16 40 52 54` (the two rows the resolver took from `even_54.jsonl`) | `collect_B54.log`, `evidence_16-40-52-54.json` |
| 58's even obligations, short children first | `./run58.sh` (`even_resolver.py 58 --short-first`, same settings), from 17:41; `./stop_on.sh PID even_triage.log 'r=58 e= 100'` stopped it after its last short child | `even_triage.log`, `even_58.jsonl` |
| is a short child of 58 P? | `./test_children.sh 58 36 44 60 68 84`, which now stops at the first child with every obligation resolved: {16,36,40,58}, at 18:02 | `test_children.log`, `resolve_16-36-40-58.jsonl` |
| B58's evidence | `THREADS=8 python collect.py resolve_16-36-40-58.jsonl '{"20": [15, "finite"]}' 16 36 40 58` (the row the resolver took from `even_58.jsonl`) | `collect_B58.log`, `evidence_16-36-40-58.json` |
| B58's certificates and replays | `REPLAY_MAX_JOBS=2 REPLAY_BUDGET_GIB=22 nice python replay.py evidence_16-36-40-58.json b58_ DIR B58` (DIR as above), October 23, 19:27, to October 24, 06:10. The largest, move 118, took 1,302 seconds natively and 14,941 in Python | `replay_B58.log`, `../b58_*-certificate.json`, `../verification/` (the per-job logs moved there too) |
| the short children of 66, 74, 78, 82 and 86 | `./short_route.sh 66 74 78 82 86` (for each R, `even_resolver.py R --short-only`, then `test_children.sh R E...` for the children E whose odd obligations are all N; same settings), from October 23, 18:03. {16,40,60,74}'s test was stopped by hand, and `./stop_on.sh PID even_triage.log 'even short-only 78 start'` stopped the run there, on October 24 at 08:59 | `even_triage.log`, `test_children.log`, `even_66.jsonl`, `even_74.jsonl`, `resolve_16-36-40-66.jsonl`, `resolve_16-40-44-66.jsonl`, `resolve_16-40-52-66.jsonl`, `resolve_16-40-66-68.jsonl`, `resolve_16-28-40-74.jsonl`, `resolve_16-36-40-74.jsonl`, `resolve_16-40-60-74.jsonl` |
| even replies from the unresolved children of {16,28,40,74} | `./deep74.sh PID` (`pair_search_any.py C --p-table --ncache-mb 8192 --threads 10 --max-states 150000000 --timeout 600`), 08:59 to 09:01. Its first two C reduce to {16,28,34,40} and {16,28,40,42}, which turned out P: the first is on Sicherman's list, and the third search found the second | `deep74.log`, `pair_any_16-28-34-40-74.log`, `pair_any_16-28-40-42-74.log`, `pair_any_16-28-40-74-98.log` (its last line was added by hand, after the search ended) |
| a larger list of known P-positions | from October 24, 09:04, `screen.py`, and so every script that imports it, adds Sicherman's list, Blok's pairing family {8,12,8n+2,8n+6} for n < 200, and the P-positions found here, each as it was found. Until 20:40 it read Sicherman's saved page; `sicherman_ppos.json` is the extract it reads now, the 265 lists on the page as updated 2026-09-28, with the same result. `route_scan.py 398` lists, for each legal even a up to 398, a move from {16,40,a} to a known P-position, if there is one | `sicherman_ppos.json`, `route_scan.txt` |
| 78, 82 and 86, with that list | `./short_route.sh 78 82 86`, from 09:04 (a run from 09:01 was stopped at 09:03 to restart with the list). 78's child {16,36,40,78} was P at 12:14. Stopped by hand at 13:27, during 82's move 84 | `even_78.jsonl`, `resolve_16-36-40-78.jsonl` |
| 82 and 86, testing each child as soon as it is found | `./short_route2.sh 82 86` (`even_resolver.py R --short-only --stop-at-needs-even`, and `route_state.py R` to see what is left), from 13:27. {16,40,44,82}'s test was stopped by hand at 14:59 | `even_82.jsonl`, `even_86.jsonl`, `resolve_16-40-44-82.jsonl`, `resolve_16-36-40-86.jsonl` |
| {16,36,40,50} and {16,36,40,70} | `./queue_family.sh PID` stopped `short_route2.sh` once {16,36,40,86}'s test ended (18:32), ran `./family36.sh 50 70` (`even_resolver.py --position 16 36 40 X --short-first`, same settings), and resumed 86's pass with `./short_route2.sh 86` at 18:54, which ended at 21:32 | `resolve_16-36-40-50.jsonl`, `resolve_16-36-40-70.jsonl` |
| unresolved obligations against the larger list, without a solver | `recheck_known.py FILE...`: at 10:15 for 66's and 74's tested children, and at 19:30, with B50 and B70, for the children still unresolved | `recheck_known.txt`, `recheck_known2.txt` |
| is {16,40,44,66} P? even replies from its three open children (36, 90, 134) | `./settle4466.sh` (`pair_search_any.py C`, the settings of `deep74.sh`), October 24, 21:34: none found | `settle4466.sh`, `settle4466.log`, `pair_any_16-36-40-44-66.log`, `pair_any_16-40-44-66-90.log`, `pair_any_16-40-44-66-134.log` |
| odd answers to 40 | `kunz_pt --p-table --ncache-mb 8192 --threads 8 --stop-at-p --max-states 200000000 --odd-list 5,7,…,33 16 40`; then `timeout 3600 kunz_pt ... --threads 10 --max-states 300000000 --odd-list 35,37,…,99 16 40`, which reached 59 | `odd_answers.*`, `odd_answers2.*` |
| odd answers to 40 from 59 | `./odd59.sh` (`kunz_pt --p-table --ncache-mb 8192 --threads 10 --stop-at-p --max-states 700000000 --odd-list 59,61,…,99 16 40`, stopped below 15 GB available or after six hours), October 24, 21:37, to October 25, 03:37: 59 to 73 fail, and the run stopped at the six-hour limit during 75 | `odd59.sh`, `odd_answers3.out`, `odd_answers3.err` |
| finite replies for B78's moves 20, 34 and 46, whose resolver replies reach Q (20 and 46) and {8,34,36} (34, on Sicherman's list) | `./b78_finite.sh` (for each move e, `kunz --threads 2 --stop-at-p --max-states 100000000 --odd-list W 16 36 40 78 e`, W the legal odd w up to 201 in the resolver's order), October 24, 22:59 to 23:01: 34 by 93 and 46 by 37, and none for 20. Then `./b78_finite20.sh`, the same for 20 with w from 203 to 601 and a 200M cap, 23:02 to 23:06: none, so 20 keeps the route through Q (by 46) | `b78_finite.sh`, `b78_finite20.sh`, `b78_finite.log`, `b78_finite_20.*`, `b78_finite_20b.*`, `b78_finite_34.*`, `b78_finite_46.*` |
| B78's evidence | `./queue_b78.sh PID` waited for `odd59.sh` to end, then ran `THREADS=8 python collect.py resolve_16-36-40-78.jsonl '{"20": [46, "Q"], "34": [93, "finite"], "46": [37, "finite"]}' 16 36 40 78`, from October 25, 03:37 | `queue_b78.sh`, `collect_B78.log`, `evidence_16-36-40-78.json` |
| B78's certificates and replays | `./replay_b78.sh SRC` (SRC the directory `collect.py` ran in) waited for `collect.py` to end, then ran `REPLAY_MAX_JOBS=2 REPLAY_BUDGET_GIB=22 nice python replay.py evidence_16-36-40-78.json b78_ DIR B78` (DIR as above; stopped below 15 GB available), October 25, 04:57 to 15:20. The 50 destinations up to 150M states were replayed natively and in Python, two at a time: the largest, move 122, took 794 seconds natively and 5,360 in Python, and move 60's Python replay took longest, 6,263 seconds. Then 90, 102 and 86, one at a time, natively and with sequential Kunz: 3,390 and 3,183 seconds for 90, 2,780 and 3,799 for 102, and 1,289 and 1,706 for 86; Kunz peaked at 9.3 GB, for 90. The log ends with `replay.py`'s "finished: 53 failed: {}" and has no "exit" line: the script's header comment was corrected while it ran, and bash, which reads a script as it runs it, then stopped with a syntax error once `replay.py` had ended | `replay_b78.sh`, `replay_B78.log`, `../b78_*-certificate.json`, `../verification/` (the per-job logs moved there too) |
| a light sweep of the odd obligations of a = 2 mod 4 from 90 to 398, beside B78's replays | `./screen90.sh` (`screen.py --odd --p-table --ncache-mb 1024 --amin 90 --threads 4 --max-states 20000000 --timeout 300`, stopped below 17 GB available), October 25, 06:00 to 12:21: 94 fails by 21 and 102 by 33; the other 76 stopped, 110 at the cap and the rest at the time limit | `screen90.sh`, `screen90.log`, `screen.jsonl` (the last 78 rows) |
| the refutations' replays for 94 and 102 | `REPLAY_MAX_JOBS=2 REPLAY_BUDGET_GIB=10 nice python replay.py evidence_16-40.json r40_ DIR '{16,40}'`, October 25, from 12:25; it skips the eight receipts verified before | `replay_r40_3.log`, `../r40_94-certificate.json`, `../r40_102-certificate.json`, `../verification/` |

The shell scripts log "(exit N)" after each run. Until the review of this
record, they took N from `$?` inside the `$(date ...)` line, which is
`date`'s status, so every such line in the logs written before that review
says 0 whatever the run did; the scripts now save the run's status first.
The same holds for the "exit" lines of `odd_answers.err` and
`odd_answers2.err`, written by hand-run commands: the second sweep ended at
its one-hour `timeout`. `odd_answers3.err` was written by `odd59.sh`, and
its "exit 143" is the six-hour limit. After the review of the
66-to-86 pass, `deep74.sh` forgets a child of 74 once another candidate's
test starts, and `short_route2.sh` stops a candidate if `route_state.py`
fails; neither changed the runs here. `route_scan.py` now counts B58 and
B78 as certified, and `route_scan.txt` is its output after the second
change (October 25), which moved only 78's row.

`even_triage.log` and `test_children.log` are complete through 86's
pass. Their "stopped" lines were written by hand or by the stopping
scripts, as were those of the pair-search logs.
`even_known.py R...` lists, without a solver, the even obligations of
{16,40,R} that no known reply settles. `pair_search_any.py` is the reply-38
search's, with `--p-table` added. `collect.py` and `replay.py` are the
reply-38 search's too, `collect.py` taking the resolver's label "opening
table" as a finite witness. For B78, `replay.py` gained a second way to
replay a destination: one above 150M states (`PYTHON_MAX`), too large for the
Python solver here, is solved alone by the native solver and then by the
sequential `kunz_solver` from the reply-38 record's pinned snapshot
(`--threads 1 --verify-memo`), which writes `kunz-receipt.json` beside the
native receipts. The audit checks that pair as `finite-witness-native-kunz`.
Nothing replayed earlier was that large. After the review of this record,
`replay.py` builds the Kunz binary from the snapshot for each such
destination instead of reusing one already built, replays Kunz again when an
earlier Kunz receipt does not record P, and exits 1 when a job fails. None
of this changed the runs here, in which every job passed.
