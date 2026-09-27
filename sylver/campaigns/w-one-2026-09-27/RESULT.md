# W's move 118 is answered by 167

**{16,26,62,98,118,167} is P** (Frobenius number 275). After move 118 from
W={16,26,62,98}, playing **167** wins.

| Destination | Frobenius | Native replay | Python replay |
| --- | ---: | --- | --- |
| {16,26,62,98,118,167} | 275 | P, 115,933,058 states, 943.63 s | P, 115,933,058 states, 7,161.52 s |

Both replays start from an empty memo. The native solver is the unchanged
repository source (`aded19fa…`), freshly built by
`sylver.verify_finite_reply`, and the Python solver is the independent
reference `sylver/solver.py`. They agree on P, the Frobenius number, and
the exact evaluated-state count, which also matches the discovery run (the
reference engine, after the flat-memo engine exhausted its memory cap). The
destination has gcd one, so this refutation needs no inherited outcome
cache, infinite-position certificate, or Quiet End Theorem.

W now has **51 of 52 obligations covered**. One move remains open:

**108**

A P destination {16,26,62,98,108,r} for any odd r would complete W's
finite coverage. W, Q, X, move 26, and opening 16 remain unresolved; W P
would establish Q={16,26,88,98} N (Q+62 = W), and U={16,26,88} P would
still also need X={16,26,82,88} N. No mathematical priority claim is made.

## Evidence and reproduction

- [w118-certificate.json](w118-certificate.json): the legal two-move path
  and its canonical finite P destination.
- [verification/w118/](verification/w118/): the replay receipt with source
  and binary fingerprints, state counts, and transcript hashes.
- [scan/ledger.jsonl](scan/ledger.jsonl) and [scan/scan_w.py](scan/scan_w.py):
  the continued scan's queries and the scanner that made them, and
  [audit.json](audit.json): the structural audit ([audit.py](audit.py)),
  which accepts a P row as a refutation only with a certificate and a
  verified replay receipt in one of the three W scan records.
- [w-frontier.json](w-frontier.json): the 51/52 summary.

```sh
python -m sylver.verify_finite_reply \
  --certificate sylver/campaigns/w-one-2026-09-27/w118-certificate.json \
  --output /tmp/w118-check --python --seconds 14400 --memory-gib 40
```

The Python replay took about two hours on a busy host and needs up to 16 GB.

## Search result and continuation

The continued ledger records 189 queries (it includes the rows of the
w-three and w-two records) with no structural failures. Every odd reply to
move 108 through 211 is classified N (by this scan or by the PR #13 evidence
graph and cache).

Late in this snapshot the scan changed engines. Rows with engine `par5`
(replies 179–189) come from `sylver/parallel_solver.cpp` with a fresh memo
per query and several threads (`engine_args`); rows with engine `psw6`
(replies 191–213) come from its shared-memo sweep mode, one memo for a
batch of candidates, whose `states` are cumulative over the batch. The
parallel engine's outcomes are exact, but its reported winning move for an
N row is *a* winning move, not necessarily the sequential engines' first,
and its state counts vary between runs. It cut the wall time per move-108
candidate from about 15 minutes to about 2, and the sweep then classified
eleven candidates in 5.4 minutes.

The ledger's last row is a P destination for move 108,
**{16,26,62,98,108,213}**, found by that sweep. Its independent replay was
in progress when this record was made, so move 108 stays open here, in
[w-frontier.json](w-frontier.json), and in [audit.json](audit.json), which
lists it as pending replay.
