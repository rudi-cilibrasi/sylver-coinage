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
| the odd obligations of 90 to 130 again, with pass A's settings: pass B | `./screen90b.sh` (`screen.py --odd --p-table --ncache-mb 8192 --threads 10 --max-states 100000000 --timeout 1800 --amin 90 --amax 198 --redo-partial`), October 25, from 15:23; `pass_c.sh` stopped it after 130, at 19:36: 90, 114 and 122 stopped at the time limit, the other six at the cap | `screen90b.sh`, `screen90b.log`, `screen.jsonl` (the last 9 rows) |
| the odd obligations pass A left for 66, 74, 86 and 82: pass C | `./pass_c.sh PID PID` (for each a, `kunz_pt --p-table --ncache-mb 8192 --threads 10 --stop-at-p --max-states 800000000 --odd-list L 16 40 a`, stopped below 15 GB available or at 6 hours for 66, 4 for 74, 3 for 86 and 82), October 25, 19:36 to 22:28: 66's three N; 74's 87 to 103 N, then 107 P. `sixty6.sh` stopped it as 86 began (that run's output was empty and is not kept; its start line is the first of `deep_86.err`), so 86 and 82 were not swept | `pass_c.sh`, `pass_c.log`, `deep_66.*`, `deep_74.*` |
| 66's even obligations whose children are long | `./sixty6.sh PID` (`even_resolver.py 66 --p-table --ncache-mb 8192 --threads 10 --short-first --max-states 400000000 --timeout 1200`), October 25, 22:28, to October 26, 08:55, when `pass_d.sh` stopped it: 20 of the 33 | `sixty6.sh`, `sixty6.log`, `even_66.jsonl` |
| the skipped odd obligations of 66's open short children {16,40,66,e}, e = 76, 84 and 116: pass D | `./pass_d.sh PID PID` (`kunz_pt` as in pass C, 2 hours each), October 26, 08:55 to 09:27, when `pass_e.sh` stopped it as its part for {16,40,52,66} began (that run's output was empty and is not kept) | `pass_d.sh`, `pass_d.log`, `deep_66+76.*`, `deep_66+84.*`, `deep_66+116.*` |
| 116's five odd obligations the resolver never tried (it gives up after four skips), then {16,40,66,76}'s even obligations: pass E | `./pass_e.sh PID` (`kunz_pt` as in pass C; then `even_resolver.py --position 16 40 66 76 --p-table --ncache-mb 8192 --threads 10 --short-first --max-states 400000000 --timeout 1200`, 10 hours at most), 09:27 to 15:26. It had begun {16,40,66,84} when `pass_f.sh` stopped it | `pass_e.sh`, `pass_e.log`, `deep_66+116b.*`, `resolve_16-40-66-76.jsonl`, `.log`, `resolve_16-40-66-84.jsonl`, `.log` (its first rows) |
| {16,40,66,76}'s open obligations 126 and 150: their skipped odd replies, then every odd reply up to 401 the resolver did not reach: pass F | `./pass_f.sh PID` (`pass_f_lists.py 16 40 66 76` gives the lists; `kunz_pt` as in pass C, 4 hours each), 15:26 to 16:56: none for 126, and 135 for 150. `pass_g.sh` stopped it as its resolve of {16,40,66,84} began | `pass_f.sh`, `pass_f.log`, `pass_f_lists.py`, `deep_76+126.*`, `deep_76+150.*` |
| the last open obligations, and odd replies above 401: pass G | `./pass_g.sh PID` (`kunz_pt` as in pass C): 126 on 403 to 1601, 4 hours; {16,40,44,66}'s open 90 and 134 on their leftover replies up to 401 (`pass_f_lists.py 16 40 44 66`), 3 hours each; then its 36 and 90 on 403 to 1601. 16:56 to 18:17: 126 by 553, 134 by 181, 36 by 447 and 90 by 463 | `pass_g.sh`, `pass_g.log`, `deep_76+126x.*`, `deep_X+90.*`, `deep_X+134.*`, `deep_X+36x.*`, `deep_X+90x.*` (X is {16,40,44,66}, B66 in the record, not the X of earlier records) |
| the positions an even reply reaches from a gcd-two position, and which are short | `peek_evens.py C...`, without a solver | |
| B66's evidence | `THREADS=8 python collect.py resolve_16-40-44-66.jsonl '{"28": [38, "B28"], "38": [28, "B28"], "36": [447, "finite"], "90": [463, "finite"], "134": [181, "finite"]}' 16 40 44 66`, October 26, 18:19 to 21:45: it stopped there, during its move 90, when `./guard90.sh PID DEADLINE` ended that solve (collect.py has no memory guard, and the solve had reached 31 GiB in 92 minutes). `finish_evidence.py` then took the 53 rows written, added 90 unsized, and solved 94, 102, 118 and 134 alone the same way, 21:45 to 22:52 | `collect_B66.log`, `guard90.sh`, `guard90.log`, `finish_evidence.py`, `finish_evidence.log`, `evidence_16-40-44-66.json` |
| cheaper witnesses for B66's moves 68 and 70 | `./alt68.sh`, `./alt70.sh` (`kunz_pt --p-table --ncache-mb 4096 --threads 8 --max-states 300000000`, without stopping at P, on every odd reply after the first witness up to 801, in the resolver's order: `alt_list.py`), October 26, 19:58 to 20:06; then `./size_alt.sh`, each new P destination solved alone by `kunz --threads 4` | `alt68.sh`, `alt70.sh`, `alt_list.py`, `alt_68.*`, `alt_70.*`, `size_alt.sh`, `size_alt.log` |
| the odd obligations pass A left for 86 and 82: pass H | `./pass_h.sh PID PID` (`kunz_pt` as in pass C, 4 hours each, after `collect.py` and `size_alt.sh` ended), October 26, 21:45, to October 27, 05:45: 86's 73 to 101 N, then the limit during 105; 82's 71 to 127 N, then the limit during 135. The first line of `deep_86.err` is pass C's, from October 25 | `pass_h.sh`, `pass_h.log`, `deep_86.*`, `deep_82.*` |
| pass H's leftovers, eight hours each: pass I | `./pass_i.sh PID` (`kunz_pt` as in pass C, on the obligations with no row in `deep_82.out` or `deep_86.out`), October 27. Its first run began with 86 and was stopped after 16 seconds; the script was then changed to take 82 first (its order and its header comment), and run again, 05:45 to 11:54: 135 by 349. Neither of its 86 runs wrote a row, and their files are not kept | `pass_i.sh`, `pass_i.log`, `deep_82x.*` |
| the even rows that odd rows settle | `python cross_rows.py 82 --b66 > cross_82.log` and `python cross_rows.py 86 > cross_86.log`, without a solver, October 27, 05:47; pass J ran the first again, which added nothing | `cross_rows.py`, `cross_82.log`, `cross_86.log`, `even_82.jsonl` and `even_86.jsonl` (their last 7 and 3 rows) |
| 82's even side: pass J | `./pass_j.sh PID`: once pass I's row for 135 was N, it stopped pass I, ran `cross_rows.py 82 --b66` again, and started `even_resolver.py 82 --p-table --ncache-mb 8192 --threads 10 --short-first --redo-open --max-states 400000000 --timeout 1200` (24 hours at most), October 27, 11:54. Its first row: 82's child {16,40,60,82} is "short: needs even", its 30 odd obligations all N, 75 and 83 (skipped on October 24) among them. `pass_k.sh` stopped it at 12:13, during its row for 68 | `pass_j.sh`, `pass_j.log`, `eighty2.log`, `even_82.jsonl` (its last row) |
| {16,40,60,82}'s 42 even obligations: pass K | `./pass_k.sh PID` (`even_resolver.py --position 16 40 60 82 --p-table --ncache-mb 8192 --threads 10 --short-first --max-states 400000000 --timeout 1200`, 16 hours at most), October 27, 12:13 to 23:34: 37 N (19 by replies it found), none refuting; 84, 90, 134, 150 and 166 open after four skips each | `pass_k.sh`, `pass_k.log`, `resolve_16-40-60-82.jsonl`, `resolve_16-40-60-82.log` |
| {16,40,60,82}'s open obligations: their skipped odd replies, then every odd reply up to 401 the resolver did not reach: pass L | `./pass_l.sh PID` (`pass_f_lists.py 16 40 60 82` gives the lists; `kunz_pt` as in pass C, 4 hours each), October 27, 23:34, when pass K ended, to October 28, 02:39. It reruns the open rows only if every row of `resolve_16-40-60-82.jsonl` is resolved or open. 84 by 145, 134 by 197, 150 by 333, 166 by 255; all 124 of 90's replies N | `pass_l.sh`, `pass_l.log`, `deep_82+60+84.*`, `deep_82+60+90.*`, `deep_82+60+134.*`, `deep_82+60+150.*`, `deep_82+60+166.*` |
| the open obligations pass L leaves, on odd replies 403 to 1601: pass M | `./pass_m.sh PID` (`kunz_pt` as in pass C, 4 hours each, for each of 90, 150 and 166 with no P row from pass L), October 28, 02:39 to 03:15: 90 by 499, so {16,40,60,82} is P and 82 fails by 60 | `pass_m.sh`, `pass_m.log`, `deep_82+60+90x.*` |
| 86's eight open odd obligations, 105 to 141, each alone: pass N | `./pass_n.sh` (`kunz_pt` as in pass C, 3 hours each; it stops at a P row), from October 28, 03:16. It was still running when this was recorded | `pass_n.sh`, `pass_n.log` (its start) |
| the answers that P-positions found for other answers refute: {16,40,x,y} refutes y by x when x is a legal move from {16,40,y} | `python mirror_scan.py > mirror_scan.log`, without a solver, October 28 (it reads the `.out`, `.err` and `.jsonl` files here; four outputs whose `.err` has no command line get their bases from this table) | `mirror_scan.py`, `mirror_scan.log` |

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

From pass B on, the long runs went one at a time: each new pass waited for
a row or a line in the running one's log, then stopped it (and its solver)
there. Most stoppers also wrote "stopped here by" into the stopped run's
log (`pass_c.log`, `pass_d.log`, `pass_e.log`, `pass_f.log`); pass C's stop
of pass B and pass D's stop of `sixty6.sh` are logged only in `pass_c.log`
and `pass_d.log`. The small jobs for B66's
evidence (`alt68.sh`, `alt70.sh`, `size_alt.sh`, `finish_evidence.py`) ran
beside `collect.py` or pass H. The last four rows of `even_66.jsonl` were
written by hand on October 26: 76, 84 and 116 as "short: needs even", once
passes D and E had swept their remaining odd obligations, and 44 as
"REFUTES r", once B66 was P by search. The 90 row of
`evidence_16-40-44-66.json` has no state count, and no Frobenius number
either; the destination's is 581.

Each long pass ran as a Claude Code background task. Stopping a pass's
shell with SIGSTOP ends that task (exit 147), and the harness then ends the
task's processes, its solver among them, within a second; a test with
`sleep` in place of the solver (not kept) showed this on October 27. So by the time a
stopper listed the stopped shell's children, there were none, and the list
in its line in `sixty6.log`, `pass_e.log`, `pass_f.log`, `pass_g.log`,
`pass_i.log` or `pass_j.log` is empty. Pass I's second 86 run was
ended this way four seconds in.
After the review of this pass, `cross_rows.py` skips a P row before reading
its winning move (a P row has none); its runs here read only N rows.
`even_82.jsonl` has the rows written by October 27, 12:13. `pass_k.sh`'s
header says pass J's row for 60 came at 12:10; it was written at about
12:02 (11:54 plus 490.5 seconds). After the review of this pass, the
header comment of `pass_h.sh` was corrected (pass C's stop); the copy
that ran differed from it there only.
On October 27 at 16:24, a test of the row check in `pass_l.sh`, before it
ran, took in the rest of the script by mistake and started pass L's first
run (84) for about two minutes beside pass K's solver, which was then
sweeping 90 (90's row then ended open, after four skips; pass L reruns
it). That run was stopped and its files deleted; the check was
then fixed (it had a syntax error and now stops pass L if it fails), and
`pass_l.sh` was not changed after it started at 16:26.
