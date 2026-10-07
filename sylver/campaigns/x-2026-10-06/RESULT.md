# X={16,26,82,88} is N: the reply 701 reaches a P-position

X is the position after 16, 26, 82 and 88 have been named: move 82 of
U={16,26,88}. On September 27 it was the last of U's 59 Quiet End
obligations still open ([U record](../u-2026-09-27/RESULT.md)). Every even
reply to X is N (Attempt 20), so X is N exactly when some odd reply reaches
a P-position. **The reply 701 does: D={16,26,82,88,701} is P**, so X is N.
D has gcd one and Frobenius number 819. Its outcome is therefore a finite
computation, of about 634 million states, that assumes no theorem and no
published position.

## The sweep that found it

Last week's sweeps refuted every odd reply up to 687. They stopped there
because this 62 GB host had run out of memory: `parallel_solver.cpp`'s
memo keys for X took 66 bytes a slot. PR #35 added `sylver/kunz_solver.cpp`.
It stores each state as its Kunz coordinates, the number of gaps in each
residue class mod 16, at 17 bytes a slot.

The new engine's first sweep shared one memo across X's odd replies from
683 on, in increasing order, on ten threads with `--verify-memo`. It used
`kunz_solver.cpp` at cfae8a6, before the review hardening, so this memo
check still made its moves with the search's own vector moves
([scan/ledger.jsonl](scan/ledger.jsonl), [scan/sweep.log](scan/sweep.log)):

| Reply | Outcome | Winning answer | Batch states | Seconds |
| ---: | --- | ---: | ---: | ---: |
| 683 | N | 727 | 620,108,668 | 414.2 |
| 685 | N | 777 | 630,645,935 | 10.6 |
| 687 | N | 611 | 630,799,559 | 0.2 |
| 689 | N | 711 | 636,023,599 | 5.4 |
| 691 | N | 637 | 636,190,686 | 0.3 |
| 693 | N | 649 | 636,459,976 | 0.3 |
| 695 | N | 697 | 639,468,164 | 3.2 |
| 697 | N | 695 | 639,651,233 | 0.2 |
| 699 | N | 613 | 639,716,533 | 0.1 |
| **701** | **P** | — | 642,846,174 | 2.8 |

The batch stopped at the P row. Its memo, 642,846,174 entries, passed the
engine's certificate check. Replies 683, 685 and 687 repeat last week's N
rows. The old engine needed 1,040 s for reply 683, and its memo filled
about 48 GB near 636 million states. The new one took 414 s.

Every odd reply below 701 is N: 203 from the audited exact cache (up to
407), 140 from the U record's verified sweeps (409–687) and 6 from this
sweep (689–699). So 701 is X's least winning odd reply; the audit reports
this as a separate verdict, which needs every one of those rows. Attempt 20
refuted every even reply, through the certified nodes C, F, G and V. Under
those nodes' assumptions, 701 is also X's least winning move. In the sweep
rows, replies 695 and 697 answer each other: {16,26,82,88,695,697} is P.

## Replays of D

A P result is replayed before it is used. The repository's usual pair of
replays is `native_solver.cpp` and the Python reference evaluator. Neither
fits D on this 62 GB host:
- `native_solver.cpp` built for 13 words used 142 bytes per state on
  {16,26,62,95,98,102} (45 million states), so D would need about 90 GB;
- the Python worker used about 125 bytes per state even on the much smaller
  {16,26,33,62,89,102} (1.7 million states, Frobenius number 119). That is
  at least 79 GB for D, and more as its keys grow with the Frobenius number.

[verification/memory/](verification/memory/) holds both runs' transcripts
(peak memory from `/usr/bin/time -v`).

Instead, two engines with independent move code each searched D
sequentially from a fresh memo ([verification/x701/](verification/x701/)):

| Run | Engine | Threads | Outcome | States | Memo check | Wall | Peak memory |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: |
| replay | `kunz_solver.cpp` (bc5460d) | 1 | P | 633,734,956 | all 633,734,956 entries, reference moves | 5,847 s | 14.2 GiB |
| replay | `parallel_solver.cpp -DSYLVER_PARALLEL_KUNZ_KEYS` (16a3e54) | 1 | P | 633,734,956 | all 633,734,956 entries, bitset moves | 10,941 s | 15.1 GiB |
| supplementary | `kunz_solver.cpp` (cfae8a6) | 10 | P | 633,744,224 | all entries | 674 s | 14.2 GiB |
| supplementary | `parallel_solver.cpp` Kunz keys | 10 | P | 633,750,099 | all entries | 2,426 s | 15.1 GiB |

- **Sequential search.** With `--threads 1` each engine follows
  `native_solver.cpp`'s recurrence exactly; on every tested position they
  print `native_solver.cpp`'s output, state count included. Each count
  should therefore equal `native_solver.cpp`'s, though it was not run on D.
  The two counts agree exactly.
- **Independent move code.** `kunz_solver.cpp` adjoins a move by a
  min-plus update of a 16-byte vector. The parallel engine's Kunz-key build
  uses its bitset shift closure and derives memo keys from bitsets by
  popcount.
- **Memo checks.** Each run certifies every entry of its memo. Both checks
  use the bitset engine's rule: an N entry names a legal move to a memoized
  P child, and every move of a P entry reaches a memoized N child or is
  answered by a smaller move. `kunz_solver.cpp` makes these checks with its
  scalar reference move, the Apéry-set definition written out, not with the
  search's vector moves.
- **Root check.** Before searching, the Kunz replay also checked D's root
  vector against the reference construction, and its largest gap against
  D's Frobenius number, 819, computed independently.
- **Threaded runs.** The supplementary runs used ten threads, so their
  counts vary with thread timing.
- **Wall times** include each memo check: on six threads for the Kunz
  replay (`--verify-threads 6`), and on one for the bitset replay.

[audit.py](audit.py) accepts D as P only from this receipt: both sequential
replays report P with Frobenius number 819, verify every entry, run the
recorded commands, and agree on the state count. It also checks that the
transcripts re-hash. Its output is [audit.json](audit.json).

## What follows

- **U is P.** X is N, so U's move 82 leads to N. With every other
  obligation already covered, U={16,26,88} is P (the [U record](../u-2026-09-27/RESULT.md),
  whose audit now re-runs this one). After the opening 16, **88 answers
  26, so the reply 26 loses**.
- **What U rests on.** U's reduction to its 59 obligations rests on the
  Quiet End Theorem. Its coverage also rests, through the certified nodes G,
  F and V and through W, on three published P-positions: {8,10,12,14} and
  {8,12,26,30} from Blok's pairing family, and Sicherman's {8,10,22}. X's
  result adds no assumption.
- **Opening 16.** The repository's certified table answers every even reply
  to the opening 16 from 2 through 24, and odd replies lose by Hutchings'
  theorem. With 26 answered here, every reply up to 26 has an answer, and
  the lowest unanswered reply is 28. Opening 16 remains unresolved.

No mathematical priority claim is made.

## Reproduction

The replayed sources are kept in [verification/x701/sources/](verification/x701/sources/):

```sh
python sylver/campaigns/x-2026-10-06/audit.py > /tmp/x-audit.json
cd sylver/campaigns/x-2026-10-06/verification/x701/sources
g++ -std=c++20 -O3 -Wall -Wextra -pedantic -Werror -pthread -march=native kunz_solver-bc5460d.cpp -o kunz-bc5460d
./kunz-bc5460d --threads 1 --verify-memo --verify-threads 6 --memo-stats 16 26 82 88 701       # about 1.6 h, 14.2 GiB
g++ -std=c++20 -O3 -Wall -Wextra -pedantic -Werror -pthread -march=native -DSYLVER_NATIVE_WORDS=13 \
    -DSYLVER_PARALLEL_KUNZ_KEYS parallel_solver-16a3e54.cpp -o pk13-16a3e54
./pk13-16a3e54 --threads 1 --verify-memo 16 26 82 88 701                                       # about 3 h, 15.1 GiB
```
