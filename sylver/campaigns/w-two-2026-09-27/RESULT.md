# W's move 70 is answered by 169

**{16,26,62,70,98,169} is P** (Frobenius number 277). After move 70 from
W={16,26,62,98}, playing **169** wins.

| Destination | Frobenius | Native replay | Python replay |
| --- | ---: | --- | --- |
| {16,26,62,70,98,169} | 277 | P, 79,594,540 states, 598.50 s | P, 79,594,540 states, 3,878.51 s |

Both replays start from an empty memo. The native solver is the unchanged
repository source (`aded19fa…`), freshly built by
`sylver.verify_finite_reply`, and the Python solver is the independent
reference `sylver/solver.py`. They agree on P, the Frobenius number, and
the exact evaluated-state count, which also matches the discovery run of the
flat-memo engine `sylver/fast_solver.cpp`. The destination has gcd one, so
this refutation needs no inherited outcome cache, infinite-position
certificate, or Quiet End Theorem.

W now has **50 of 52 obligations covered**. These two moves remain open:

**108, 118**

A single P destination {16,26,62,98,108,118} would answer both, but it has
an unproved infinite odd tail, so each move needs its own witness. W, Q, X,
move 26, and opening 16 remain unresolved; W P would establish
Q={16,26,88,98} N (Q+62 = W), and U={16,26,88} P would still also need
X={16,26,82,88} N. No mathematical priority claim is made.

## Evidence and reproduction

- [w70-certificate.json](w70-certificate.json): the legal two-move path and
  its canonical finite P destination.
- [verification/w70/](verification/w70/): the replay receipt with source and
  binary fingerprints, state counts, and transcript hashes.
- [scan/ledger.jsonl](scan/ledger.jsonl): the continued scan's queries (the
  scan of [w-three-2026-09-27](../w-three-2026-09-27/README.md), same method),
  and [audit.json](audit.json): its structural audit, which accepts a P row
  as a refutation only with a certificate and a verified replay receipt.
- [w-frontier.json](w-frontier.json): the 50/52 summary.

```sh
python -m sylver.verify_finite_reply \
  --certificate sylver/campaigns/w-two-2026-09-27/w70-certificate.json \
  --output /tmp/w70-check --python --seconds 14400 --memory-gib 40
```

The Python replay needs over an hour and up to 16 GB.

## Search result and continuation

The continued ledger records 164 queries (it includes the rows of the
w-three record) with no structural failures. Queries that exhausted memory
under the flat-memo engine are retried with the reference engine, whose
node-based memo needs less peak memory.

The ledger also contains one more P destination, found near the end of this
snapshot: **{16,26,62,98,118,167}** (115,933,058 states in its single
discovery run, by the reference engine). Its independent replay was in
progress when this record was made, so move 118 stays open here, in
[w-frontier.json](w-frontier.json), and in [audit.json](audit.json), which
lists it as pending replay.
