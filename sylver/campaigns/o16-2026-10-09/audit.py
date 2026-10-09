#!/usr/bin/env python3
"""Ledger of the answers to the even replies after the opening 16, up to 200.

For each legal even reply r to the opening 16 up to LIMIT (r not a multiple of
16) that has a known answer, this ledger records an answer a such that {16,r,a}
is P, with exactly one of these kinds of evidence:

1. ``certified-table``: (r, a, destination) is a row of
   ``sylver.short_certificates.OPENING_16_EVEN_RESPONSES``, which
   ``verify_opening_16_even_responses`` checks in tests/test_sylver_solver.py;
2. ``certified-node``: {16,r,a} is a node of ``sylver.short_certificates.NODES``;
3. ``campaign``: {16,r,a} is exactly the position that a campaign audit in this
   repository finds P (its committed audit.json, whose reproducibility the
   campaign's own test checks);
4. ``finite-witness``: {16,r,a} has gcd one, and a certificate here has a
   ``verified`` native and Python replay receipt (as in the campaign audits);
5. ``finite-witness-native-kunz``: as 4, for destinations too large for the
   Python evaluator on this host: a native_solver.cpp replay and a sequential
   kunz_solver.cpp replay (``--threads 1 --verify-memo``) of the pinned source,
   with equal state counts.

Odd replies to 16 lose by Hutchings' theorem and are not listed. The ledger
reports every answered even reply and the lowest legal even reply that has no
answer yet. Output: ``python audit.py > audit.json``.
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
from sylver.short_certificates import NODES, OPENING_16_EVEN_RESPONSES  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

LIMIT = 200
OPENING = (16,)
CAMPAIGNS = {'u-2026-09-27': None, 'y-2026-10-07': None, 'z-2026-10-08': 'Z'}   # nested section, if any
# reply: (answer, evidence, reference)
ANSWERS = {
    26: (88, 'campaign', 'u-2026-09-27'),
    28: (58, 'campaign', 'y-2026-10-07'),
    30: (56, 'campaign', 'z-2026-10-08'),
    34: (20, 'certified-node', 'T'),
    36: (23, 'finite-witness', None),
    56: (30, 'campaign', 'z-2026-10-08'),
    58: (11, 'finite-witness', None),
    62: (37, 'finite-witness-native-kunz', None),
    86: (33, 'finite-witness-native-kunz', None),
    88: (26, 'campaign', 'u-2026-09-27'),
    90: (17, 'finite-witness', None),
    140: (13, 'finite-witness', None),
    156: (21, 'finite-witness', None),
}
KUNZ_OPTIONS = ['--threads', '1', '--verify-memo', '--verify-threads', '6', '--memo-stats']
KUNZ_SNAPSHOT = HERE / 'verification/sources/kunz_solver-0668ae4.cpp'
KUNZ_SOURCE_SHA256 = '4b6221788c1e76805bbf7d680a493e7c21c9664a2ef3274ff50487302cd2c672'   # sylver/kunz_solver.cpp at 0668ae4 (unchanged since 48c1968)


def transcript_states(name, stdout, dest, frobenius):
    """The state count a solver's stdout reports for a P result at ``dest``, or None."""
    lines = stdout.splitlines()
    if len(lines) != 1:
        return None
    if name == 'native':
        parts = lines[0].split()
        if parts[:3] != ['P', 'winning_move=none', f'frobenius={frobenius}'] or len(parts) != 4:
            return None
        return int(parts[3].split('=')[1]) if parts[3].startswith('states=') else None
    try:
        row = json.loads(lines[0])
    except ValueError:
        return None
    ok = (isinstance(row, dict) and row.get('position') == list(dest) and row.get('outcome') == 'P'
          and row.get('frobenius') == frobenius)
    return row.get('states') if ok else None


def kunz_states(directory, dest, frobenius):
    """The state count of a verified sequential kunz_solver replay of ``dest`` in ``directory``, or None."""
    receipt = directory / 'kunz-receipt.json'
    files = [directory / f'kunz-{stream}.txt' for stream in ('stdout', 'stderr')]
    if not (receipt.exists() and all(f.exists() for f in files)):
        return None
    r = json.loads(receipt.read_text())
    snapshot = (directory / str(r.get('source_snapshot', ''))).resolve()
    if (snapshot != KUNZ_SNAPSHOT.resolve() or r.get('source_sha256') != KUNZ_SOURCE_SHA256
            or hashlib.sha256(snapshot.read_bytes()).hexdigest() != KUNZ_SOURCE_SHA256
            or [hashlib.sha256(f.read_bytes()).hexdigest() for f in files] != [r.get('stdout_sha256'),
                                                                               r.get('stderr_sha256')]):
        return None
    states = r.get('states')
    stdout, stderr = files[0].read_text().splitlines(), files[1].read_text().splitlines()
    ok = (type(states) is int and r.get('returncode') == 0 and r.get('outcome') == 'P'
          and r.get('position') == list(dest) and r.get('frobenius') == frobenius
          and r.get('source') == 'sylver/kunz_solver.cpp'
          and r.get('command', [None])[1:] == [*KUNZ_OPTIONS, *map(str, dest)]
          and stdout == [f'P winning_move=none frobenius={frobenius} states={states}', f'verified entries={states}']
          and stderr.count(f'kunz_solver: memo verified ({states} entries)') == 1
          and [line.strip() for line in stderr if line.strip().startswith('Exit status')] == ['Exit status: 0'])
    return states if ok else None


def finite_witness(r, a, native_kunz):
    cert, receipt = HERE / f'o{r}-certificate.json', HERE / f'verification/o{r}/receipt.json'
    if not (cert.exists() and receipt.exists()):
        return None
    c, rec = json.loads(cert.read_text()), json.loads(receipt.read_text())
    native, python = rec.get('runs', {}).get('native'), rec.get('runs', {}).get('python')
    if (rec.get('status') != 'verified' or native is None or (python is None) != native_kunz
            or type(native.get('states')) is not int or (python is not None and type(python.get('states')) is not int)):
        return None
    dest = position((*OPENING, r, a))
    ok = (rec['certificate_sha256'] == hashlib.sha256(cert.read_bytes()).hexdigest() and c['parent'] == list(OPENING)
          and c['opponent_move'] == r and c['reply'] == a and gcd(*dest) == 1
          and list(dest) == c['destination'] == rec['position'] and c['destination_outcome'] == 'P'
          and frobenius_number(dest) == c['frobenius'] == rec['frobenius']
          and native['states'] == (kunz_states(receipt.parent, dest, c['frobenius']) if native_kunz
                                   else python['states']))
    for name, run in (('native', native),) + ((() if native_kunz else (('python', python),))):
        files = [HERE / f'verification/o{r}/{name}-{stream}.txt' for stream in ('stdout', 'stderr')]
        ok = ok and (run['outcome'] == 'P' and run['returncode'] == 0 and not run['timed_out']
                     and run['frobenius'] == c['frobenius'] and run['command'][-len(dest):] == list(map(str, dest))
                     and all(f.exists() for f in files)
                     and hashlib.sha256(files[0].read_bytes()).hexdigest() == run['stdout_sha256']
                     and hashlib.sha256(files[1].read_bytes()).hexdigest() == run['stderr_sha256'])
        ok = ok and transcript_states(name, files[0].read_text(), dest, c['frobenius']) == native['states']
    if not ok:
        return None
    return {'certificate': str(cert.relative_to(ROOT)), 'receipt': str(receipt.relative_to(ROOT)),
            'states': native['states']}


def campaign_p(name, dest):
    """True when campaign ``name``'s committed audit finds exactly ``dest`` P."""
    if name not in CAMPAIGNS:
        return False
    report = json.loads((ROOT / 'sylver/campaigns' / name / 'audit.json').read_text())
    section = report[CAMPAIGNS[name]] if CAMPAIGNS[name] else report
    return report.get('outcome') == 'P' and section.get('outcome') == 'P' and section.get('position') == list(dest)


def check(r, a, kind, ref, table):
    """The evidence row for the answer a to the reply r, or None."""
    if not (legal(OPENING, r) and legal(position((*OPENING, r)), a)):
        return None
    dest = position((*OPENING, r, a))
    if kind == 'certified-table':
        return {'destination': ref} if table.get(r) == (a, ref) else None
    if kind == 'certified-node':
        node = next((n for n in NODES if n.name == ref), None)
        return {'destination': key(dest), 'node': ref} if node and key(node.generators) == key(dest) else None
    if kind == 'campaign':
        return {'destination': key(dest), 'campaign': f'sylver/campaigns/{ref}/audit.json'} if campaign_p(ref, dest) else None
    if kind in ('finite-witness', 'finite-witness-native-kunz'):
        row = finite_witness(r, a, kind == 'finite-witness-native-kunz')
        return {'destination': key(dest), **row} if row else None
    return None


def main():
    table = {m: (resp, dest) for m, resp, dest in OPENING_16_EVEN_RESPONSES}
    report = {'opening': 16, 'limit': LIMIT, 'answers': {}, 'unanswered': [], 'failures': []}
    for r in range(2, LIMIT + 1, 2):
        if r % 16 == 0:
            continue
        if r in table:
            a, kind, ref = table[r][0], 'certified-table', table[r][1]
        elif r in ANSWERS:
            a, kind, ref = ANSWERS[r]
        else:
            report['unanswered'].append(r)
            continue
        row = check(r, a, kind, ref, table)
        if row is None:
            report['failures'].append(f'reply {r}: the answer {a} has no accepted {kind} evidence')
            report['unanswered'].append(r)   # a failed row answers nothing
            continue
        report['answers'][str(r)] = {'answer': a, 'evidence': kind, **row}
    kinds = {}
    for row in report['answers'].values():
        kinds[row['evidence']] = kinds.get(row['evidence'], 0) + 1
    report['summary'] = {'answered': len(report['answers']), 'by_evidence': kinds,
                         'lowest_unanswered': report['unanswered'][0] if report['unanswered'] else None}
    print(json.dumps(report, indent=2))
    return 0 if not report['failures'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
