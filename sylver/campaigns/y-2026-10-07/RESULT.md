# Y={16,28,58} is P: 58 answers the reply 28 to the opening 16

Y is the position after the opening 16, the reply 28 and the answer 58.
**Y is P**, so after the opening 16 the reply 28 loses: 58 answers it.

The opening-16 replies now answered:
- **Even replies 2–24:** the repository's certified table answers each one.
- **26:** answered by 88, through U={16,26,88} ([U record](../u-2026-09-27/RESULT.md)).
- **28:** answered by 58, here.
- **Odd replies:** lose by Hutchings' theorem.

The lowest unanswered reply is now 30. Opening 16 remains unresolved.

## The certificate

Y has gcd two, and its half {8,14,29} is a quiet ender (Frobenius number 63),
so Y is short. By the Quiet End Theorem, Y is P exactly when each of its
**54 obligations** leads to an N-position. They are the 32 even moves 2g for
the gaps g of the half, and the half's 22 odd gaps above 1. [audit.py](audit.py)
lists them twice, with the arena referee's profile and with an independent
coin-sum count, and accepts only these kinds of evidence ([audit.json](audit.json)):

| Evidence | Obligations | Moves |
| --- | ---: | --- |
| winning reply to a certified P-position | 6 | 4 (→6, C), 6 (→4, C), 8 (→14, E), 12 (→14, F), 14 (→8, E), 22 (→12, P0) |
| finite witness, native and Python replays | 48 | every other obligation |
| **total** | **54** | |

- **Certified node.** The listed reply reaches a P-position certified in
  `sylver/short_certificates.py`: C={4,6}, E={8,14}, F={12,14,16} or
  P0={12,16,22}. The audit checks legality and identity.
- **Finite witness.** A certificate `y<m>-certificate.json` names the reply
  w to the obligation m. The destination Y+m+w has gcd one.
  `python -m sylver.verify_finite_reply --python` replayed it from empty
  memos with `native_solver.cpp` and with the Python reference evaluator
  ([verification/](verification/)). Both report P with the same state
  count, and the audit re-hashes every transcript.
  - The 48 replays (38 distinct destinations; some obligations share one)
    take 711,534,629 states together.
  - The largest is Y+98+181 = {16,28,58,98,181}: 160,339,405 states,
    Frobenius number 291.

Y rests on the Quiet End Theorem, which reduces it to its obligations. Through
the nodes E, F and P0, it also rests on two members of Blok's infinite
pairing family, {8,10,12,14} and {8,12,18,22}; `sylver/eight_twelve.py`
audits that pairing strategy. Unlike U and W, Y does not depend on
Sicherman's {8,10,22}.

## How Y was found

{16,28} = 4·{4,7}, and {4,7} is a coprime pair, so it is a quiet ender. The
search for a winning reply to 28 ran in three stages. The scripts are kept in
[scan/](scan/) with their working paths.

1. **Odd replies.** The odd gaps of {4,7}, namely 3, 5, 9, 13 and 17, all
   lose: {16,28,m} is N for each, exactly. `analyze_opening_16.py 28` agrees.
2. **Short even candidates.** For r ≡ 2 (mod 4), {16,28,r} has half
   {8,14,r/2}. When r/2 is odd and lies in {4,7}, that half is a gluing of
   the symmetric semigroup {4,7}, so it is symmetric and {16,28,r} is short.
   For r ≥ 10, this holds for r = 22, 30 and every r ≡ 2 (mod 4) from 38 on,
   but not for 10, 18, 26 or 34. (6 and 14 give {6,16} and {14,16}, which
   are already known to be N.) For the short candidates:
   - one shared-memo `kunz_solver.cpp` sweep checks every odd obligation
     ([scan/odd_filter.jsonl](scan/odd_filter.jsonl)). Up to r = 142, 10
     candidates fall to an odd obligation, and 19 are *odd-complete*.
   - for r = 38, 50 and 58, each even obligation was then given a winning
     reply ([scan/](scan/)). The reply either reaches a known P-position or
     is a finite odd witness found by a sweep. A short child needs only its
     own obligations; a long child is swept further. The other 15
     odd-complete candidates, 62 to 142, were not resolved.
   - these search sweeps ran without `--verify-memo`, except for the deep
     sweep for r = 50. The certificate above replays everything it uses.
3. **Results.**
   - **r = 22** is refuted: its move 12 reaches {12,16,22} = P0, which is P.
   - **r = 58** closes: all 54 obligations are answered. This is Y.
   - **r = 50**: the search record indicates that {16,28,50} is P too, but
     this is unverified discovery output.
     - Its last obligation, 118, reaches {16,28,50,118}, a long child.
     - A deep sweep found the reply 461: {16,28,50,118,461} is P, from an
       8-thread batch whose memo of 273,426,772 entries passed
       `--verify-memo` ([scan/deep50/](scan/deep50/)).
     - Its other witnesses were neither memo-verified nor replayed.
     - Its moves 20 and 38 go through node M, which needs O and so
       Sicherman's {8,10,22}. A certificate for {16,28,50} would rest on
       {8,10,22}; Y's does not.
   - **r = 38** is open. Its last obligation, 40, reaches the short position
     {16,28,38,40}. All of its odd obligations are N, so it is N only
     through an even reply to a P-position. None was found among the six
     short positions it reaches; the other 17 are long and were not examined
     ([scan/pair_38_40.log](scan/pair_38_40.log)).

Y was certified because it needs no deep witness and does not rest on
Sicherman's {8,10,22}.

No mathematical priority claim is made.

## Reproduction

```sh
python sylver/campaigns/y-2026-10-07/audit.py > /tmp/y-audit.json
python -m sylver.verify_finite_reply --certificate sylver/campaigns/y-2026-10-07/y98-certificate.json \
    --output /tmp/y98 --python --seconds 36000 --memory-gib 40
```
