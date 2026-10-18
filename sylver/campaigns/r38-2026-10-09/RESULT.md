# Reply 38 after the opening 16: four P-positions refute five answers

After the opening 16, the lowest reply with no certified answer is 38
([the ledger](../o16-2026-10-09/RESULT.md)). {16,38} has gcd two and a short
half, {8,19}. So by the Quiet End Theorem, a move answers 38 only if it is
one of {16,38}'s 98 obligations: 35 odd moves and 63 even ones.

This record certifies four P-positions:

| Position | Half | Its Frobenius number | Obligations |
| --- | --- | ---: | ---: |
| I={16,20,22,24} | {8,10,11,12} | 25 | 21 |
| B28={16,28,38,40} | {8,14,19,20} | 45 | 38 |
| B24={16,24,38,44} | {8,12,19,22} | 45 | 38 |
| B56={16,38,56,60} | {8,19,28,30} | 69 | 56 |

**Correction (October 10).** This record first called all four new. I and B24
are on George Sicherman's [list of P-positions](https://sicherman.net/sylver/ppos.html)
(last updated September 28), so for them it is an independent confirmation.
B28 and B56 are not on that list.

They refute five candidate answers to 38:
- **24 and 44 do not answer 38.** {16,38,24} and {16,38,44} each move to B24,
  by 44 and by 24 respectively, so both are N.
- **28 and 40 do not answer 38.** {16,38,28} and {16,38,40} each move to
  B28, by 40 and by 28 respectively.
- **56 does not answer 38.** {16,38,56} moves to B56 by 60.

The audit also checks six refutations through certified nodes:
- 4 and 6 (6 and 4 reach C={4,6});
- 8 and 14 (14 and 8 reach E={8,14});
- 12 (14 reaches F={12,14,16});
- 22 (12 reaches P0={12,16,22}).

**One question from the Y record is settled.** The Y record left open
whether 38 answers the reply 28, that is, whether {16,28,38} is P. It is N:
its move 40 reaches B28.

No certified answer to 38 is known, so **38 remains the lowest reply
without one**. By search, though, **72 answers 38** (October 18;
[below](#the-search-for-an-answer-to-38)). Opening 16 remains unresolved.

## The certificate

All four positions are short, so each is P exactly when each of its
obligations leads to N. The obligations are the even moves 2g for the gaps
g of the half, and the half's odd gaps above 1. [audit.py](audit.py) lists
them twice, with the arena referee's profile and with an independent
coin-sum count. It audits I first, then B28, B24 and B56
([audit.json](audit.json)), and accepts:

| Evidence | I | B28 | B24 | B56 |
| --- | ---: | ---: | ---: | ---: |
| finite witness, native and Python replays | 17 | 30 | 31 | 42 |
| finite witness, native and Kunz replays | — | — | — | 4 |
| certified node | 4 | 8 | 6 | 6 |
| an earlier position of this audit is P | — | — | 1 (I) | 4 (B24, B28) |

Each finite witness is a certificate `<prefix><move>-certificate.json`, in
the schema the campaign records use.
- `python -m sylver.verify_finite_reply --python` replayed it from empty
  memos with `native_solver.cpp` and with the Python reference evaluator
  ([verification/](verification/)). Both report P with the same state
  count.
- B56's four witnesses above 175 million states were replayed
  differently. They are its moves 122, 84, 90 and 74, at 179,722,136 to
  423,748,850 states.
  - Each has a `native_solver.cpp` replay and a sequential
    `kunz_solver.cpp` replay (`--threads 1 --verify-memo`) with equal state
    counts.
  - The Kunz source is kept in
    [verification/sources/](verification/sources/), and the audit pins its
    hash and checks the command each transcript records.
  - The Python evaluator needs about 125 to 180 bytes per state. These four
    would need 22 to 76 GB of this 62 GB host, which other work shares.
    Earlier records drew the same line: Z replayed a 145-million-state
    witness in Python, and its 262- and 297-million-state ones by Kunz.
  - B56's three witnesses from 106 to 138 million states (moves 100, 106
    and 42) have Python replays.
- The replays total 1,810,987,248 states:
  - 656,850,201 replayed natively and in Python;
  - 1,154,137,047 replayed natively and by Kunz.
- The largest witness is B56's move 74 answered by 205,
  {16,38,56,60,74,205}, at 423,748,850 states.

The audit then checks the eleven refutations: each listed move is legal and
reaches B24, B28, B56 or a certified node.

**What it rests on.** The certified nodes used are C, D, E, F, J and P0.
Through them the certificate rests on the Quiet End Theorem, the pairing
family {8,10,12,14} and {8,12,18,22}, as Y's does. It does not rest on
Sicherman's {8,10,22}: I's moves 8 and 10 and B28's move 50, which the
search first answered through {8,10,22} and the node M, have finite
witnesses instead.

No mathematical priority claim is made.

## The search for an answer to 38

The search is recorded in [scan/](scan/). Its sweeps ran without
`--verify-memo`. So apart from the eleven refutations the audit checks
(through B24, B28, B56 and the nodes C, E, F and P0), this section is
discovery output, not certified.

| Obligations of {16,38} | Count | P | N so far | Open |
| --- | ---: | ---: | ---: | ---: |
| odd | 35 | 0 | 32 | 3 |
| even, short child | 17 | 1 (72) | 16 | 0 |
| even, long child | 46 | 0 | 20 | 26 |

By search, 72 is P, so **72 answers 38**, and the other open obligations no
longer matter to that question. `python scan/status.py` derives this table's
statuses from the logs.

- **Odd.** The ledger's scan showed the 24 smallest odd candidates are N.
  One more shared-memo sweep here showed that 71, 69, 77 and 79 are N, then
  stopped during 85 at its 1,400,000,000-state cap.
  - On October 10 a queue ran each of the other seven alone, on 8 threads
    with a cap of 1,700,000,000 states (`--max-states`;
    [scan/odd_queue.sh](scan/odd_queue.sh)). 85, 87, 93 and 101 are N, won
    by 105, 273, 83 and 33.
  - 109, 117 and 125 stopped at that cap, and again when each was retried
    alone at 2,100,000,000 states, whose memo took about 50.5 GB of this
    62.5 GiB host ([scan/odd_retry.sh](scan/odd_retry.sh)). They are open:
    each needs more than 2.1 billion states, and the cap cannot rise much
    further here.
  - On October 12 the three were attacked from below. A winning move m of
    X = {16,38,W} makes X+m P, so a sweep solved the children X+m, cheapest
    first: the even ones singly and the odd ones in batches of 20 sharing
    one memo and its cap, of 200,000,000 states for the even children (and,
    in a first run, some odd ones) and then 250,000,000 for the odd ones
    ([scan/child_sweep.py](scan/child_sweep.py), which applies the partner
    rule to settle children without solving them).
    - Of the 173, 179 and 185 children of 109, 117 and 125, 75, 70 and 69
      are N, and none classified is P. Four of the N, 100 and 71 for 117 and
      111 and 171 for 125, follow by the partner rule from rows the sweep
      recorded after those children had hit the cap; the sweep as run left
      them capped.
    - Each sweep stopped after its 40th capped child, alone or partway
      through a batch. 58, 71 and 78 children were never classified, among
      them 106, 164 and 88, which the even sweeps' three-hour limit cut off
      mid-solve.
    - Two probes paired the three: {16,38,109,117} is N (won by 22), and
      {16,38,117,125} stopped at 400,000,000 states (125 = 109 + 16 is not a
      move after 109).
- **Short even.**
  - For a = 6, 12, 20, 60 and 136, an odd move wins from {16,38,a}
    ([scan/odd_filter.jsonl](scan/odd_filter.jsonl)).
  - Certified nodes refute 4, 6, 8, 12 and 22, as above; the audit checks
    these.
  - B24, B28 and B56 refute 24, 28, 40, 44 and 56, above.
  - The other short candidates form a ladder with 56 and 136: a = 56 + 16k,
    for 72, 88, 104 and 120.
    - Since 16 is in every position here, a candidate's obligation b, for a
      lower rung b, leads back to {16,38,b}. So at most one rung is P: a P
      rung refutes every rung above it.
    - 136 falls to an odd obligation (37) and 56 to B56. An answer among the
      short candidates must be the first P rung among 72, 88, 104 and 120.
  - 72 and 88 are odd-complete: every odd obligation is N. For 72, one
    sweep on October 18 named a winning move for each of the 25
    (`scan/odd72_all.*`).
    - 72's obligation 56 is answered through B56. The deep replies 129 and
      69 answer its obligations 58 and 66.
    - 72's long children 68, 78 and 84 have no even reply into a short
      P-position. Their odd winners came from the hunt below: 139 for 84,
      257 for 68 and, last, 367 for 78. The hardest of their odd replies each need
      from about 300 million to over a billion states: those from 81 on for
      78, from 87 on for 84, and from about 150 on for 68 (in the hunt
      below, some of 68's replies from 191 on stopped at its
      1,000,000,000-state cap).
    - Every short child of 72 is N, so a refutation of 72 would need a long
      P-position, which the Quiet End Theorem cannot certify.
    - By October 11 every even obligation of {16,38,72} had been run:
      {16,38,72,170} is won by 71 (`scan/even_72.*`), and a round-robin hunt
      over its open long children found {16,38,72,132} won by 75 and
      {16,38,72,84} won by 139 (`scan/hunt.*`). The open ones were then 68,
      78, 100, 106, 116 and 154.
    - The hunt ran on until October 12 at 04:52 without another witness: of
      its 87 later rows, 29 are N and 58 stopped at the 1,000,000,000-state
      cap.
    - From 09:01 on October 12 it retried the replies it had capped, now
      with a cap of 1,600,000,000 states. By 17:50 it had solved 24 of them,
      each needing between 1.00 and 1.41 billion states; none stopped at the
      new cap. {16,38,72,154} is won by 119 and {16,38,72,106} by 137.
    - The retries went on to October 13 at 03:40 without another witness:
      33 more replies are N, and 116+151 stopped at the new cap. A pass over
      fresh replies at that cap, each step going to the child searched least
      far in its order, ran from 03:42 to October 14 at 14:29: 13 N, and 85
      stopped at the cap.
    - From October 14 the hunt used the P-table engine
      (`sylver/kunz_solver.cpp --p-table`, PR #56; a prototype of it until
      October 15), which keeps only P-positions in its memo, on the replies
      the cap had stopped. By October 16 at 12:40 it had settled 53 of them,
      each with 49 to 80 million P-positions, and 8 more by the partner rule.
      All are N: no witness.
    - From October 16 at 13:25 it went on through the 25 replies left in
      that retry queue, three hours at most each. By 21:24 it had settled
      ten more as N and one by the partner rule, and 116+219 had run out of
      time. Then, at 22:01, it found {16,38,72,116}+229 P (81,370,519
      P-positions, 37 minutes), so 229 wins {16,38,72,116}. It is the first
      witness the P-table engine found, and then the deepest in its child's
      order: 113th counting from 0, where the hunt's four earlier witnesses
      came 37th to 68th. A rerun with another build and schedule
      (`scan/check_116_229.*`: the same source at `-O2` for any x86-64
      instead of `-O3 -march=native`, 2 threads instead of 10, split depth 4
      instead of 6, a 4 GB cache instead of 16 GB) also found it P, with
      81,373,145 P-positions in 7 hours 37 minutes; which P-positions get
      stored depends on the search order, so the counts differ. Both runs
      use the same algorithm, so the rerun guards against faults of build
      and schedule, not of method.
    - 116's last three queued replies, 233, 235 and 237, were dropped once
      229 won it. The retry queue ran out on October 17 at 04:10: the nine
      retries after the witness, of 78 and 100, are N. From then on the
      hunt took fresh replies of 68, 78 and 100 (`hunt.py 1200000000
      --balance`).
    - On fresh replies, after 241 and 243 of 100 were N, it found
      {16,38,72,100}+245 P at 07:57 (70,825,107 P-positions, 26 minutes),
      and after 255 of 68 was N, {16,38,68,72}+257 P at 10:22 (33,735,838
      P-positions, 15 minutes). So 245 wins {16,38,72,100} and 257 wins
      {16,38,68,72}. They are 121st and 127th in their children's orders,
      counting from 0. Reruns with the build and schedule that checked 229
      (`scan/check_100_245.*`, then `scan/check_68_257.*`, queued by
      `scan/check_queue.sh`) also found both P, with 71,023,435 P-positions
      in 5 hours and 33,806,189 in 1 hour 40 minutes. `scan/witness_check.py`
      finds none of the hunt's seven witnesses at odds with its other rows:
      none wins a reply recorded N on its child that is still legal after
      it, and none is one move from another of the 305 P-positions the rows
      name.
    - That left 78, 72's only open long child: one P reply of 78 would
      settle that 72 answers 38, and 78 being P would refute it. The hunt
      ran it alone from October 17 at 10:22: 37 more replies N by search
      and 19 by the partner rule. Then, on October 18 at 01:51, it found
      {16,38,72,78}+367 P (56,699,024 P-positions, 20 minutes), so 367 wins
      {16,38,72,78}. 367 is 182nd in 78's order, counting from 0 (the
      child's Frobenius number with it is 505), and every reply of 78
      before it in that order is N. A rerun with the build and schedule
      that checked 229 (`scan/check_78_367.*`, after the hunt had ended)
      also found it P, with 56,854,380 P-positions in 2 hours 2 minutes.
      `scan/witness_check.py` finds all eight of the hunt's witnesses
      consistent with its 600 rows and the 335 P-positions they name.
    - So, by search, every obligation of {16,38,72} is N: its 25 odd ones
      (above) and its 43 even ones (32 by the even resolver, 56 through
      B56, 58 and 66 by the deep replies 129 and 69, and eight long
      children by the hunt's witnesses). **{16,38,72} is P, and 72 answers
      38.** This is discovery output, not certified: the runs behind it
      were not replayed, and the reruns of the last four witnesses share
      their engine's algorithm. Since then 61 of the 68 obligations have
      been certified ([the certification record](../c72-2026-10-18/RESULT.md));
      seven of the eight long children the hunt settled remain search
      results.
    - 88, 104 and 120 each move by 72 back to {16,38,72} (16 generates
      them from 72), so they are N, whatever their unfinished odd
      obligations.
- **Long even.** A long candidate is N as soon as one winning reply is
  found.
  - Sweeps found a winning odd reply for 2 (3), 10 (9), 18 (5), 26 (97),
    30 (271), 34 (53), 36 (123), 50 (79), 58 (11), 78 (27), 94 (43),
    98 (31), 100 (41) and 174 (45). The deeper pass below found 52 (143),
    110 (59) and 218 (49), and the second deeper pass found 42 (233) and
    46 (147).
  - 14 moves to E by 8.
  - 31 stayed open within the sweeps' state caps: 42, 46, 52, 62, 66, 68,
    74, 82, 84, 90, 106, 110, 116, 122, 126, 132, 138 and 142, and, from the
    map's continuation on October 10, 148, 154, 158, 164, 170, 180, 186, 196,
    202, 212, 218, 234 and 250.
  - For 42, the 106 odd replies classified are all N, and four more (205,
    213, 215 and 221) were not classified: their batches stopped at the state
    cap or the 1,800-second timeout. The second deeper pass below found 233.
  - So every long candidate has been searched, but mostly shallowly. The map
    gave each batch of odd replies a cap of 300,000,000 states up to 36,
    500,000,000 from 42 to 50, 150,000,000 from 52 to 218, and 700,000,000
    for 234 and 250, and gave up on a candidate after four batches stopped.
    27 of the 31 open candidates had only the 150,000,000-state cap (see the
    scan README).
  - A deeper pass on October 10 and 11 (`scan/deep_long.*`) queued those 27,
    one at a time, resuming near where the map had stopped and retrying the
    replies it skipped, with a cap of 700,000,000 states per batch and an
    hour per candidate. It finished on October 11 at 15:15: 52 is won by 143,
    110 by 59 and 218 by 49 (in eight minutes), and the other 24 ran out of
    time (106 without finishing a batch).
  - A second deeper pass on October 12 (`scan/deep_long2.*`) took first the
    four long candidates the first pass had not covered, 42, 46, 234 and 250:
    two hours each at the same cap per batch, leaving out the replies already
    classified (but for three of the map's; see the scan README). 42 is won by
    233 (found in 26 minutes) and 46 by 147 (in 12 minutes). 234 and 250 ran
    out of time: they classified five and four replies (all N), and six
    replies of each were skipped when their batch hit the 700,000,000-state
    cap. 26 long candidates are open; the pass has not yet returned to the
    other 24.

## Reproduction

```sh
python sylver/campaigns/r38-2026-10-09/audit.py > /tmp/r38-audit.json
python -m sylver.verify_finite_reply --certificate sylver/campaigns/r38-2026-10-09/b24_90-certificate.json \
    --output /tmp/b24_90 --python
```
