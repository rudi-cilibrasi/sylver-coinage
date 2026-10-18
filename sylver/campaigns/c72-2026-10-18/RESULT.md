# {16,38,72}: 60 of its 68 obligations certified

By search, 72 answers the reply 38 to the opening 16: {16,38,72} is P
([the reply-38 record](../r38-2026-10-09/RESULT.md#the-search-for-an-answer-to-38)).
{16,38,72} has gcd two and a short half, {8,19,36}. So by the Quiet End
Theorem it is P exactly when each of its 68 obligations (25 odd moves, 43
even ones) leads to an N-position. This record certifies 60 of them.
The other eight rest on search alone, so **{16,38,72} is not yet
certified P**: 72 answers 38 by search, and 38 is still the lowest reply to
16 without a certified answer.

| Evidence | Obligations |
| --- | ---: |
| finite witness, native and Python replays | 47 |
| finite witness, native and sequential Kunz replays | 2 |
| certified node (C, E, F, P0) | 6 |
| B24, B28 or B56, which the reply-38 audit certifies | 5 |
| **certified** | **60** |
| search witness only (the hunt's) | 8 |

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
is the runner's log for the 35 replays it ran with Python (the two large
ones' runs printed to its own output, and `c72_3` was run by hand).
`replay.py` does not check its children's exit codes: the audit rejects any
receipt that is not a complete, matching replay. [sizes.json](sizes.json)
holds the state counts that `kunz --threads 8 <destination>` (the reply-38
scan's build) found for each destination before the replays, used only to
order them and size their memory limits; they differ slightly from the
sequential counts.

Seven routes reach small positions the opening table already certifies:
{2,3} (by 3 → 2 and 2 → 3), {5,16,18} (5 → 18 and 18 → 5), {6,7,16}
(7 → 6) and {9,10,16} (9 → 10 and 10 → 9). They are replayed here like the
others.

## The other certified routes

- **Nodes.** 4 and 6 reach C={4,6} (by 6 and 4), 8 and 14 reach E={8,14}
  (by 14 and 8), 12 reaches F={12,14,16} (by 14) and 22 reaches
  P0={12,16,22} (by 12), all certified in `sylver/short_certificates.py`.
- **The reply-38 audit's positions.** 24 and 44 reach B24 (by 44 and 24),
  28 and 40 reach B28 (by 40 and 28), and 56 reaches B56 (by 60, since
  {16,38,72,56} is {16,38,56}). This audit runs the reply-38 audit afresh
  on its own certificates and receipts, and requires it to find them P.

## What is left: the hunt's eight witnesses

The long children {16,38,72,e} for e in 68, 78, 84, 100, 106, 116, 132 and
154 are N by witnesses the reply-38 hunt found P by search alone:

| Obligation | Reply | Engine | Search size | Rerun |
| ---: | ---: | --- | ---: | --- |
| 132 | 75 | memo | 355,076,111 states | — |
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
certify. A native replay needs memory in proportion to its states. 132 → 75,
at 355 million states, is smaller than the 401,815,231-state destination
replayed here, so it looks within reach on this 62 GiB host; the other three
memo witnesses, at 1 billion states or more, look beyond it. The P-table
runs give no total count: their N-cache statistics bound 68 → 257 at about
690 million states, so it may be within reach too, and the other three are
less clear.

**What it rests on.** The Quiet End Theorem, which makes these 68
obligations all of {16,38,72}'s; the nodes C, E, F and P0; the reply-38
audit (B24, B28 and B56, which rest on the nodes C, D, E, F, J and P0); and
the solvers that replayed each finite witness. None of it rests on
Sicherman's {8,10,22}. The eight search witnesses rest on the reply-38
search engines alone.

## Reproduction

```sh
python sylver/campaigns/c72-2026-10-18/audit.py > /tmp/c72-audit.json
python -m sylver.verify_finite_reply --certificate sylver/campaigns/c72-2026-10-18/c72_5-certificate.json \
    --output /tmp/c72_5 --python
```
