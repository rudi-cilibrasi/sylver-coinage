# W's move 102 is answered by 95

**{16,26,62,95,98,102} is P.** Its Frobenius number is 203.
After move 102 from W={16,26,62,98}, playing **95** therefore wins.

Independent native and Python replays start with empty memos and agree on
**P, Frobenius number 203, and exactly 44,985,582 states**. The native
replay takes 169.22 seconds and Python takes 771.78 seconds.
The destination has gcd one, so this branch
refutation needs no inherited outcome cache, infinite P-position certificate,
or Quiet End Theorem.

This closes the next branch after PR #5's move-134 result. W now has
**47 of 52 obligations covered**, with these five moves still unresolved:

**70,86,92,108,118**

W, Q, X, move 26, and opening 16 remain unresolved. Other W obligations
retain their previously recorded dependencies. No mathematical priority
claim is made.

## Evidence and reproduction

- [w102-certificate.json](w102-certificate.json): the legal two-move path
  and its canonical finite P destination.
- [verification/receipt.json](verification/receipt.json): independent replay
  status, source fingerprints, evaluated-state counts, and transcript hashes.
- [evidence/batch-0002/receipt.json](evidence/batch-0002/receipt.json): the
  discovery receipt, including the completed P row before interruption.
- [evidence/frontier.json](evidence/frontier.json): the discovery frontier.
- [w-frontier.json](w-frontier.json): the verified 47/52 summary, linked
  to the certificate and completed replay by hashes.
- [audit.json](audit.json): bookkeeping and structural checks, separate from
  finite solver replay.

From the repository root, use a new output directory:

```sh
python -m sylver.verify_finite_reply \
  --certificate sylver/campaigns/w-six-2026-09-22/w102-certificate.json \
  --output /tmp/w102-check --python
```

Without `--python`, only the standalone native solver runs. Neither mode
loads the campaign cache. The verifier rejects invalid paths and false P
claims and, with Python requested, requires both independent implementations
to agree on the exact evaluated-state count.

## Search result and continuation

The bounded search completed **15 finite queries: 14 N and one P** in
**400.99 seconds (6.68 minutes)** of native search runtime. The second batch
stopped as soon as the P result was observed; nine remaining requests were
not classified. Its 45,063,267 cumulative states include earlier queries,
so that count is different from the standalone replay's cost.

An additional discovery destination, **{16,26,33,62,89,102}**, has its own
fresh native and Python replays. Both agree on P, Frobenius number 119,
and exactly **1,721,485 states**, in 2.52 and 15.14 seconds respectively.
This refutes odd 89 from W+102 by reply 33; it does not by itself classify
W+102. See [the cross-check certificate](w102-89-crosscheck-certificate.json)
and [receipt](crosscheck/receipt.json).

The first unclassified odd replies in the remaining branches are:

| W move | First unclassified odd reply |
| --- | --- |
| 70 | 95 |
| 86 | 97 |
| 92 | 103 |
| 108 | 91 |
| 118 | 97 |

These are starting points for further finite witness searches, not bounds
on where a winning reply might occur. A finite prefix of N outcomes does
not prove any of these infinite positions P. The original 305,011-row
outcome cache and both exact solver implementations are unchanged.

[remaining-pairs.json](remaining-pairs.json) refreshes the four unresolved
even-pair targets: (70,108), (86,92), (86,108), and (108,118). Proving any
one of their common destinations P would refute both moves from W. Every
listed destination still has an unproved infinite odd tail; these are
future targets, not certificates.
