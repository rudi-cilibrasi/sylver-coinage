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
| the finite refutations of answers to 40 | `THREADS=2 python refutations.py 10:9 18:5 26:11 30:17 42:23 50:11 70:37 62:61`, then again without `62:61`, whose destination took 286,533,125 states | `refutations_with_62.log`; `refutations.log`, `evidence_16-40.json` |
| certificates and replays | `REPLAY_MAX_JOBS=2 REPLAY_BUDGET_GIB=8 python replay.py evidence_16-20-46.json q DIR Q`, and `REPLAY_BUDGET_GIB=10 ... evidence_16-40.json r40_ DIR '{16,40}'` (DIR the record's directory) | `replay_Q.log`, `replay_r40.log`, `../q*-certificate.json`, `../r40_*-certificate.json`, `../verification/` (each job's log, which `replay.py` writes beside the certificates, was moved there) |
| 54's even obligations, short children first | `./short_first.sh` (`even_resolver.py 54 --short-first --p-table --ncache-mb 8192 --threads 10 --max-states 100000000 --timeout 300`), from 15:53; `./stop_on.sh PID even_triage.log 'r=54 e=  92'` stopped it after its last short child | `even_triage.log`, `even_54.jsonl` |
| is a short child of 54, with every odd obligation N, itself P? | `./test_children.sh 54 52 60 68 76` (`even_resolver.py --position 16 40 54 E --short-first`, same settings), from 16:05; stopped by hand at 16:28, once {16,40,52,54} was P | `test_children.log`, `resolve_16-40-52-54.jsonl`, `resolve_16-40-54-60.jsonl` (partial) |
| a finite reply for B54's move 24, in place of the node K | `kunz --threads 8 --stop-at-p --max-states 100000000 --odd-list W 16 40 52 54 24` (W as above): none | `b54_finite_24.out`, `.err` |
| B54's evidence | `THREADS=8 python collect.py resolve_16-40-52-54.jsonl '{"36": [21, "finite"], "26": [11, "finite"]}' 16 40 52 54` (the two rows the resolver took from `even_54.jsonl`) | `collect_B54.log`, `evidence_16-40-52-54.json` |
| 58's even obligations, short children first | `./run58.sh` (`even_resolver.py 58 --short-first`, same settings), from 17:41; `./stop_on.sh PID even_triage.log 'r=58 e= 100'` stopped it after its last short child | `even_triage.log`, `even_58.jsonl` |
| is a short child of 58 P? | `./test_children.sh 58 36 44 60 68 84`, which now stops at the first child with every obligation resolved: {16,36,40,58}, at 18:02 | `test_children.log`, `resolve_16-36-40-58.jsonl` |
| B58's evidence | `THREADS=8 python collect.py resolve_16-36-40-58.jsonl '{"20": [15, "finite"]}' 16 36 40 58` | `collect_B58.log`, `evidence_16-36-40-58.json` |
| odd answers to 40 | `kunz_pt --p-table --ncache-mb 8192 --threads 8 --stop-at-p --max-states 200000000 --odd-list 5,7,…,33 16 40`; then `timeout 3600 kunz_pt ... --threads 10 --max-states 300000000 --odd-list 35,37,…,99 16 40`, which reached 59 | `odd_answers.*`, `odd_answers2.*` |

`even_triage.log` and `test_children.log` are kept up to the start of the
next step, a short-children pass over 66, 74, 78, 82 and 86 (`--short-only`
and `short_route.sh`, which will be recorded with its results).
`even_known.py R...` lists, without a solver, the even obligations of
{16,40,R} that no known reply settles. `pair_search_any.py` is the reply-38
search's, with `--p-table` added. `collect.py` and `replay.py` are the
reply-38 search's too, `collect.py` taking the resolver's label "opening
table" as a finite witness.
