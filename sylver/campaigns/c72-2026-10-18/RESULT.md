# {16,38,72}: 61 of its 68 obligations certified

By search, 72 answers the reply 38 to the opening 16: {16,38,72} is P
([the reply-38 record](../r38-2026-10-09/RESULT.md#the-search-for-an-answer-to-38)).
{16,38,72} has gcd two and a short half, {8,19,36}. So by the Quiet End
Theorem it is P exactly when each of its 68 obligations (25 odd moves, 43
even ones) leads to an N-position. This record certifies 61 of them.
The other seven rest on search alone, so **{16,38,72} is not yet
certified P**: 72 answers 38 by search, and 38 is still the lowest reply to
16 without a certified answer.

| Evidence | Obligations |
| --- | ---: |
| finite witness, native and Python replays | 47 |
| finite witness, native and sequential Kunz replays | 3 |
| certified node (C, E, F, P0) | 6 |
| B24, B28 or B56, which the reply-38 audit certifies | 5 |
| **certified** | **61** |
| search witness only (the hunt's) | 7 |

[audit.py](audit.py) checks every row ([audit.json](audit.json)).

## The finite witnesses

For 49 obligations the search recorded a reply that leaves a finite
position, {16,38,72,m,v} with gcd one: the 25 odd obligations
(`../r38-2026-10-09/scan/odd72_all.out`), 22 even ones the even resolver
answered with an odd move (`even_72.jsonl`), and 58 and 66 (the deeper
sweeps' replies 129 and 69). Partner routes often meet: 69 → 66 and 66 → 69
both reach {16,38,66,69,72}. So the 49 routes reach 38 destinations, and
[make_certificates.py](make_certificates.py) wrote one certificate per
destination, `c72_<m>-certificate.json`, in the schema the campaign records
use, named after the first obligation that reaches it. The audit checks
each obligation's own move and reply against the certified destination.

Every destination was replayed from empty memos on October 18 from 05:34
to 11:41: {2,3} (`c72_3`) by hand as a first check, the rest by
[replay.py](replay.py) from 05:35, several at a time within a memory
budget:
- 36 destinations, up to 145,567,304 states, with
  `python -m sylver.verify_finite_reply --python`: `native_solver.cpp` and
  the Python reference evaluator, which report P with the same state count;
- the two largest, {16,38,71,72,170} (299,519,162 states) and
  {16,38,58,72,129} (401,815,231), with `native_solver.cpp` and a
  sequential `kunz_solver.cpp` replay (`--threads 1 --verify-memo`) built
  from the source snapshot the reply-38 audit pins, as for B56's largest
  witnesses. The counts agree.

The replays total 1,366,033,291 states ([verification/](verification/)).
Each receipt records its limits, commands, hashes and counts; `c72_<m>.log`
is the runner's log for the 35 replays it ran with Python (the large ones'
runs printed to its own output, and `c72_3` was run by hand).
`replay.py` checks the exit code only of the large native runs (c72_58,
c72_132 and c72_170), not of the Python-path runs or the Kunz runs: the
audit rejects any receipt that is not a complete, matching replay.
[sizes.json](sizes.json) holds the state counts that `kunz --threads 8
<destination>` (the reply-38 scan's build) found for each destination before
the replays, used only to order them and size their memory limits; they
differ slightly from the sequential counts.

Eleven routes reach positions certified before. Seven reach the opening
table's finite P-positions: {2,3} (by 3 → 2 and 2 → 3), {5,16,18} (5 → 18
and 18 → 5), {6,7,16} (7 → 6) and {9,10,16} (9 → 10 and 10 → 9). Four reach
destinations the reply-38 audit replayed as finite witnesses: {13,15,16,38}
(13 → 15), {7,15,16} (15 → 7), {13,16,20,38} (20 → 13) and {12,16,23,38}
(23 → 12), with the same state counts here. They are replayed here like the
others.

## The hunt's witness for 132

Of the eight long children the hunt settled, {16,38,72,132} has the
smallest witness: 75, whose destination {16,38,72,75,132} the memo engine
found P with 355,076,111 states. `make_certificates.py 132` wrote its
certificate, and on October 18 it was replayed like the largest finite
witnesses: `native_solver.cpp` from 12:50 to 13:33 (355,061,923 states; about
29 GB resident, the largest reading of a 30-second log,
[verification/c72_132-memory.log](verification/c72_132-memory.log)) and the
sequential, memo-verified `kunz_solver.cpp` until 14:23, with the same
count. So 132 is now certified too: 39
destinations, 1,721,095,214 replayed states in all.

## The other certified routes

- **Nodes.** 4 and 6 reach C={4,6} (by 6 and 4), 8 and 14 reach E={8,14}
  (by 14 and 8), 12 reaches F={12,14,16} (by 14) and 22 reaches
  P0={12,16,22} (by 12), all certified in `sylver/short_certificates.py`.
- **The reply-38 audit's positions.** 24 and 44 reach B24 (by 44 and 24),
  28 and 40 reach B28 (by 40 and 28), and 56 reaches B56 (by 60, since
  {16,38,72,56} is {16,38,56}). This audit runs the reply-38 audit afresh
  on its own certificates and receipts, and requires it to find them P.

## What is left: seven of the hunt's witnesses

The long children {16,38,72,e} for e in 68, 78, 84, 100, 106, 116 and 154
are N by witnesses the reply-38 hunt found P by search alone (132, the
eighth, is certified above):

| Obligation | Reply | Engine | Search size | Rerun |
| ---: | ---: | --- | ---: | --- |
| 84 | 139 | memo | 980,837,915 states | — |
| 154 | 119 | memo | 1,119,121,060 states | — |
| 106 | 137 | memo | 1,263,036,473 states | — |
| 116 | 229 | P-table | 81,370,519 P-positions | `check_116_229.*` |
| 100 | 245 | P-table | 70,825,107 P-positions | `check_100_245.*` |
| 68 | 257 | P-table | 33,735,838 P-positions | `check_68_257.*` |
| 78 | 367 | P-table | 56,699,024 P-positions | `check_78_367.*` |

The memo engine counts every state it stores; the P-table engine stores
only P-positions, typically a few percent of the states it visits. The
reruns used another build and schedule of the same engine, so they do not
certify.

A native replay needs memory in proportion to its states: about 80 bytes a
state for Frobenius numbers below 320 (132 → 75 took about 29 GB), more
for wider states (the solver's states have ⌊F/64⌋ + 1 words; 4- and 5-word
states take the same 64-byte hash node). The three memo
witnesses left, at about a billion states or more, would need some 75 GB or
more, beyond this 62 GiB host. For the P-table witnesses a plain-memo count
was missing, so the smallest, 68 → 257, was counted with the memo engine
(the reply-38 scan's `kunz` at 0668ae4, before the P-table mode existed,
8 threads; [plain_68_257.out](plain_68_257.out)): its destination
{16,38,68,72,257} is P, with 1,494,012,288 states (36 GB resident, 15
minutes). That checks this witness without the P-table mode's code; it
shares the search both modes use, so it is still search, not a certificate.
With Frobenius number 355, a native replay of it would need some 135 GB or
more. The other three P-table witnesses store more P-positions than 257's,
so they are likely larger still. Certifying these seven looks to need a
larger machine or another method.

**What it rests on.** The Quiet End Theorem, which makes these 68
obligations all of {16,38,72}'s; the nodes C, E, F and P0; the reply-38
audit (B24, B28 and B56, which rest on the nodes C, D, E, F, J and P0);
through those nodes, as in the reply-38 record, the pairing family
{8,10,12,14} and {8,12,18,22}; and the solvers that replayed each finite
witness. None of it rests on Sicherman's {8,10,22}. The seven search
witnesses rest on the reply-38 search engines alone.

## Reproduction

```sh
python sylver/campaigns/c72-2026-10-18/audit.py > /tmp/c72-audit.json
python -m sylver.verify_finite_reply --certificate sylver/campaigns/c72-2026-10-18/c72_5-certificate.json \
    --output /tmp/c72_5 --python
```
