#!/usr/bin/env python3
"""Audit of X={16,26,82,88}: its odd reply 701 reaches a P-position, so X is N.

X is the position after 16, 26, 82 and 88 have been named: U={16,26,88}'s
move 82. The reply 701 is legal (X has only even elements) and reaches
D={16,26,82,88,701}, which has gcd one and Frobenius number 819, so D's
outcome is a finite computation that assumes no theorem and no published
position. This script accepts D as P only from the replay receipt in
``verification/x701/``:

1. two sequential (``--threads 1``) searches with independent move code,
   ``sylver/kunz_solver.cpp`` (Kunz-coordinate byte vectors) and
   ``sylver/parallel_solver.cpp`` built with ``-DSYLVER_PARALLEL_KUNZ_KEYS``
   (bitsets), must each report P with Frobenius number 819 and certify
   their whole memo (``verified entries=`` equal to the state count), and
   the two state counts must be equal: each is native_solver.cpp's
   sequential count for D;
2. each run's stdout and stderr transcripts are re-hashed against the
   receipt; the command recorded by ``/usr/bin/time`` in the stderr
   transcript must be exactly the expected sequential, verified search of D
   (with exit status 0), and the engine's own "memo verified" line must
   count every state;
3. each run's exact source, kept in ``verification/x701/sources/``, must
   re-hash to the receipt's ``source_sha256``.

It also re-derives D, the legality of 701 and D's Frobenius number, and
checks the shared-memo sweep that found D (``scan/ledger.jsonl``): every
row's position and Frobenius number, its memo check, and that its last row
is the P row for 701. Finally it classifies X's odd replies below 701, from
the audited exact cache (``move26_data/periodicity_x.cache``, up to 407), the
verified sweeps of the U record (``campaigns/u-2026-09-27/scan/ledger-x.jsonl``,
409 to 687) and this record's sweep. Only if all are N does it report 701 as
X's least winning odd reply (a separate verdict: X is N either way).
Output: ``python audit.py > audit.json``.
"""
import hashlib
import json
import sys
from math import gcd
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from sylver.arena.common import key, legal, position  # noqa: E402
from sylver.short_certificates import minimal_generators  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

X = (16, 26, 82, 88)
REPLY = 701
RECEIPT = HERE / 'verification/x701/receipt.json'
LEDGER = HERE / 'scan/ledger.jsonl'
X_CACHE = ROOT / 'sylver/move26_data/periodicity_x.cache'
U_LEDGER = ROOT / 'sylver/campaigns/u-2026-09-27/scan/ledger-x.jsonl'
# Each replay: its source, a build flag it needs, its engine's name in stderr, and its exact options.
ENGINES = {'kunz': ('sylver/kunz_solver.cpp', None, 'kunz_solver',
                    ['--threads', '1', '--verify-memo', '--verify-threads', '6', '--memo-stats']),
           'bitset': ('sylver/parallel_solver.cpp', '-DSYLVER_PARALLEL_KUNZ_KEYS', 'parallel_solver',
                      ['--threads', '1', '--verify-memo'])}


def replays(destination, frobenius, failures):
    """The receipt's two sequential replays, checked; returns their summaries."""
    if not RECEIPT.exists():
        failures.append('no replay receipt')
        return {}
    receipt = json.loads(RECEIPT.read_text())
    if receipt.get('position') != list(destination) or receipt.get('frobenius') != frobenius:
        failures.append('the receipt is for another position')
    summaries = {}
    for name, (source, flag, engine, options) in ENGINES.items():
        run = receipt.get('runs', {}).get(name)
        if run is None:
            failures.append(f'no {name} replay')
            continue
        files = [RECEIPT.parent / f'{name}-{stream}.txt' for stream in ('stdout', 'stderr')]
        if not all(f.exists() for f in files) or [hashlib.sha256(f.read_bytes()).hexdigest() for f in files] != [
                run.get('stdout_sha256'), run.get('stderr_sha256')]:
            failures.append(f'the {name} transcripts do not match the receipt')
            continue
        snapshot = RECEIPT.parent / str(run.get('source_snapshot', ''))
        if not snapshot.is_file() or hashlib.sha256(snapshot.read_bytes()).hexdigest() != run.get('source_sha256'):
            failures.append(f'the {name} source snapshot does not match the receipt')
            continue
        states = run.get('states')
        stdout, stderr = files[0].read_text().splitlines(), files[1].read_text().splitlines()
        # /usr/bin/time's record: exactly one command line and one exit status.
        timed = [line.strip() for line in stderr if line.strip().startswith('Command being timed')]
        exits = [line.strip() for line in stderr if line.strip().startswith('Exit status')]
        command = (timed[0].split('"', 1)[1].rsplit('"', 1)[0].split()
                   if len(timed) == 1 and timed[0].count('"') == 2 else [])
        # The engine's own lines: its memo check, and kunz_solver's --memo-stats line.
        verified = f'{engine}: memo verified ({states} entries)'
        engine_lines = [line for line in stderr if line.startswith(f'{engine}:')]
        stats = [line for line in engine_lines if line.startswith(f'kunz_solver: memo entries={states} slots=')]
        expected = [*options, *map(str, destination)]
        ok = (isinstance(states, int) and states > 0
              and stdout == [f'P winning_move=none frobenius={frobenius} states={states}',
                             f'verified entries={states}']
              and engine_lines.count(verified) == 1 and len(engine_lines) == 1 + len(stats)
              and len(stats) == ('--memo-stats' in options)
              and command[1:] == expected and command and Path(command[0]).name == run.get('command', [''])[0]
              and run.get('command', [])[1:] == expected and exits == ['Exit status: 0']
              and run.get('outcome') == 'P' and run.get('returncode') == 0 and run.get('source') == source
              and (flag is None or flag in run.get('build', '').split()))
        if not ok:
            failures.append(f'the {name} replay is not a verified sequential P result for {key(destination)}')
            continue
        summaries[name] = {'engine': source + (f' ({flag})' if flag else ''), 'commit': run.get('commit'),
                           'states': states, 'verified_entries': states,
                           'elapsed_seconds': run.get('elapsed_seconds'), 'max_rss_kib': run.get('max_rss_kib')}
    if len(summaries) == len(ENGINES) and len({s['states'] for s in summaries.values()}) != 1:
        failures.append('the sequential replays disagree on the state count')
    return summaries

def sweep(failures):
    """The shared-memo sweep from reply 683 that found D: rows checked and summarized."""
    rows = [json.loads(line) for line in LEDGER.read_text().splitlines()]
    refuted, found = [], None
    for row in rows:
        p = position((*X, row['r']))
        if list(p) != row['position'] or frobenius_number(p) != row['frobenius'] or not legal(X, row['r']):
            failures.append(f"sweep row {row['r']}: position, Frobenius number or legality mismatch")
            continue
        if row['status'] != 'ok' or not row.get('memo_verified') or row['outcome'] not in ('N', 'P'):
            failures.append(f"sweep row {row['r']}: not a verified result")
            continue
        if row['outcome'] == 'N':
            w = row.get('winning_move')
            if w is None or not legal(p, w):
                failures.append(f"sweep row {row['r']}: illegal winning move")
                continue
            refuted.append(row['r'])
        else:
            found = row
    if found is None or found['r'] != REPLY or rows[-1] is not found:
        failures.append('the sweep does not end with the P row for 701')
    shown = LEDGER.relative_to(ROOT) if LEDGER.is_relative_to(ROOT) else LEDGER
    return {'ledger': str(shown), 'engine': rows[0]['engine'] if rows else None,
            'replies': [row['r'] for row in rows], 'refuted_N': refuted,
            'P_reply': found['r'] if found else None,
            'batch_states_at_P': found['states'] if found else None}


def odd_replies_below(failures):
    """X's odd replies below 701, classified by the cache and the verified sweeps."""
    cache = {}
    for line in X_CACHE.read_text().splitlines():
        k, v = line.split()
        if v not in ('0', '1'):
            failures.append(f'cache row {k}: value {v!r}')
            continue
        cache[k] = 'P' if v == '1' else 'N'
    classified = {}
    for r in range(3, REPLY, 2):
        k = key(minimal_generators((*X, r)))
        if k in cache:
            classified[r] = ('cache', cache[k])
    for ledger, source in ((U_LEDGER, 'U record sweep'), (LEDGER, 'this sweep')):
        for row in (json.loads(line) for line in ledger.read_text().splitlines()):
            if row['r'] >= REPLY or row['status'] != 'ok' or not row.get('memo_verified'):
                continue
            p = minimal_generators((*X, row['r']))
            w = row.get('winning_move')
            if (list(p) != row['position'] or frobenius_number(p) != row['frobenius'] or row['outcome'] not in ('N', 'P')
                    or (row['outcome'] == 'N' and (w is None or not legal(p, w)))):
                failures.append(f"{source} row {row['r']}: inconsistent")
                continue
            earlier = classified.get(row['r'])
            if earlier is not None and earlier[1] != row['outcome']:
                failures.append(f"reply {row['r']}: {earlier[0]} says {earlier[1]}, {source} says {row['outcome']}")
                continue
            classified.setdefault(row['r'], (source, row['outcome']))
    by_source = {}
    for source, outcome in classified.values():
        by_source[f'{source} {outcome}'] = by_source.get(f'{source} {outcome}', 0) + 1
    unclassified = [r for r in range(3, REPLY, 2) if r not in classified]
    p_replies = sorted(r for r, (_, outcome) in classified.items() if outcome == 'P')
    return {'classified': by_source, 'unclassified': unclassified, 'P_replies': p_replies,
            'all_N': not unclassified and not p_replies}


def main():
    failures = []
    destination = position((*X, REPLY))
    frobenius = frobenius_number(destination)
    if not legal(X, REPLY) or gcd(*destination) != 1 or list(destination) != [16, 26, 82, 88, REPLY]:
        failures.append('701 is not a legal reply of X reaching a gcd-one position')
    below = odd_replies_below(failures)
    report = {'position': list(X), 'reply': REPLY, 'destination': key(destination),
              'destination_frobenius': frobenius, 'destination_outcome': None,
              'replays': replays(destination, frobenius, failures), 'sweep': sweep(failures),
              'odd_replies_below_701': below, 'least_winning_odd_reply': None, 'failures': failures}
    if not failures:
        report['destination_outcome'] = 'P'
        if below['all_N']:
            report['least_winning_odd_reply'] = REPLY
    report['outcome'] = 'N' if not failures else 'unknown'
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
