# W's move 134 is answered by 85

**{16,26,62,85,98,134} is P.** Its Frobenius number is 203.
Therefore, after move 134 from W={16,26,62,98}, playing **85** wins.

Independent native and Python replays start with empty memos and agree on
**P, Frobenius number 203, and exactly 37,192,385 states**. The native
replay takes 128.30 seconds and Python takes 593.79 seconds.
The destination has gcd one, so
this new branch refutation needs no inherited outcome cache, infinite
P-position certificate, or Quiet End Theorem.

The resulting W frontier has **46 of 52 obligations covered**, with six
even moves still unresolved:

**70,86,92,102,108,118**

W, Q, X, move 26, and opening 16 remain unresolved. The other W obligations
retain their previously recorded dependencies. No mathematical priority
claim is made.

## Evidence and reproduction

* [w134-certificate.json](w134-certificate.json): the legal two-move path
  and its finite P destination.
* [verify_w134.py](verify_w134.py): checks the semigroup identity and
  replays the destination from an empty memo.
* [verification/receipt.json](verification/receipt.json): standalone
  verification status, source fingerprints, counts, and transcript hashes.
* [deep/batch-0002/receipt.json](deep/batch-0002/receipt.json): discovery
  receipt; the completed P row was flushed before the batch was stopped.
* [deep/frontier.json](deep/frontier.json): the reduced six-move frontier.
* [w-frontier.json](w-frontier.json): the verified 46/52 summary, linked
  to the certificate and completed replay by hashes.
* [initial-audit.json](initial-audit.json) and [deep-audit.json](deep-audit.json):
  bookkeeping and structural audits, distinct from finite solver replay.

From the repository root, use a new output directory:

```sh
python sylver/campaigns/w-seven-2026-09-22/verify_w134.py \
  --output /tmp/w134-check --python
```

Without `--python`, only the standalone native solver is run. Neither mode
loads the campaign cache. The verifier also checks that the two independent
implementations agree on the exact state count when Python is requested.

## What the bounded search learned

The search completed **35 finite queries: 34 N and one P**, stopping at the
first reply that refutes one of W's seven open moves. It used
**1,344.49 seconds (22.4 minutes)** of
native search runtime, within the one-hour cap. Verification and campaign
bookkeeping are separate from that search budget.

The initial ten 90-second batches completed eight queries. Repeated
timeouts prompted a change to longer batches; the next two completed
14 and 13 queries in 217.98 and 225.07 seconds. Each batch shared one
initially empty exact memo across its requests. These are different
workloads, not a controlled speedup benchmark. The successful batch had
57,095,963 cumulative states; that is not the cost of the final P query
alone. The standalone replay above measures that destination separately.

One additional new finite P destination,
{16,26,37,62,87,92,98}, has an independent Python/native cross-check.
Both implementations agree on its outcome, Frobenius number 123, and
exact count of 3,458,311 states; see [python-crosscheck.json](python-crosscheck.json)
and [native-crosscheck.json](native-crosscheck.json).

The branch closure came from an odd finite witness after immediate short
even replies had already been ruled out. The result supports continuing
shared finite searches on the six remaining branches, with enough time
per batch to reuse expensive intermediate work.

The first odd replies still unclassified in the resulting ledger are:

| W move | First unclassified odd reply |
| --- | --- |
| 70 | 91 |
| 86 | 91 |
| 92 | 95 |
| 102 | 89 |
| 108 | 87 |
| 118 | 91 |

These are search starting points, not bounds on where a winning reply
could occur. Some larger replies are already refuted by exact routing.
