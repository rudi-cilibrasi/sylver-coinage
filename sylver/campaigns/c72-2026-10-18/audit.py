#!/usr/bin/env python3
"""{16,38,72} after the opening 16: which of its Quiet End obligations are certified N.

{16,38,72} has gcd two and a short half, {8,19,36}, so by the Quiet End Theorem it is P exactly when
each of its obligations (the even moves 2g for the gaps g of the half, and the half's odd gaps above 1)
leads to an N-position. The reply-38 search found every one N (../r38-2026-10-09/RESULT.md), so by
search {16,38,72} is P and 72 answers the reply 38. This audit lists the obligations twice, with the
arena referee's profile and with the reply-38 audit's coin-sum count, and accepts for an obligation m
with the listed reply v:

1. ``finite-witness``: a c72 certificate in this directory whose finite destination is {16,38,72,m,v},
   with a verified native and Python replay receipt (checked as the reply-38 audit checks its own).
   Partner routes share destinations, so the certificate may name another obligation; the audit checks
   that m and v are legal and reach that destination.
2. ``finite-witness-native-kunz`` (the certificates in NATIVE_KUNZ only): as 1, with a sequential
   kunz_solver.cpp replay (--threads 1 --verify-memo, from the source the reply-38 audit pins) in place
   of the Python one, as for B56's largest witnesses.
3. ``certified-node``: v reaches a P-position certified in ``sylver.short_certificates.NODES``.
4. ``certified-position``: v reaches B24, B28 or B56, which the reply-38 audit finds P
   (its committed audit.json, with no failures).

Any other listed route is ``search-witness``: the reply-38 hunt found {16,38,72,m,v} P by search
(scan/hunt.jsonl), which is not certified. The outcome is "P" only if every obligation has evidence 1 to
4; with search witnesses left it is "unknown", and ``search_only`` lists them. A route whose evidence
fails is a failure. Output: ``python audit.py > audit.json``.
"""
import hashlib
import importlib.util
import json
import sys
from math import gcd
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R38 = ROOT / 'sylver/campaigns/r38-2026-10-09'
sys.path.insert(0, str(ROOT))
from sylver.arena.common import key, legal, position, profile  # noqa: E402
from sylver.short_certificates import NODES  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

_spec = importlib.util.spec_from_file_location('r38_audit', R38 / 'audit.py')
r38 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r38)

PARENT = (16, 38, 72)
# obligation m: its reply v, as the reply-38 search recorded it (odd72_all.out, even_72.jsonl, the
# deeper sweeps of 58 and 66, and hunt.jsonl); make_certificates.py writes the finite routes' certificates
ROUTES = {
    2: 3, 3: 2, 4: 6, 5: 18, 6: 4, 7: 6, 8: 14, 9: 10, 10: 9, 11: 46, 12: 14, 13: 15, 14: 8, 15: 7, 17: 61,
    18: 5, 20: 13, 21: 98, 22: 12, 23: 12, 24: 44, 25: 52, 26: 121, 28: 40, 29: 55, 30: 59, 31: 59,
    33: 77, 34: 53, 36: 123, 37: 52, 39: 138, 40: 28, 41: 87, 42: 77, 44: 24, 45: 50, 46: 11, 47: 50,
    49: 90, 50: 45, 52: 25, 53: 19, 56: 60, 58: 129, 60: 17, 61: 17, 62: 45, 66: 69, 68: 257, 69: 66,
    74: 25, 77: 33, 78: 367, 82: 35, 84: 139, 85: 45, 90: 49, 94: 37, 98: 21, 100: 245, 106: 137,
    116: 229, 122: 33, 132: 75, 138: 27, 154: 119, 170: 71,
}
NODE_ROUTES = {4: 'C', 6: 'C', 8: 'E', 12: 'F', 14: 'E', 22: 'P0'}
POSITION_ROUTES = {24: 'B24', 28: 'B28', 40: 'B28', 44: 'B24', 56: 'B56'}
NATIVE_KUNZ = {'c72_58', 'c72_170'}     # destinations above 150 million states


def certificates():
    """{destination key: (certificate path, its name)} for the c72 certificates in this directory."""
    out = {}
    for path in sorted(HERE.glob('c72_*-certificate.json')):
        out[tuple(json.loads(path.read_text())['destination'])] = (path, path.name.removesuffix('-certificate.json'))
    return out


def finite_witness(m, v, certs):
    dest = position((*PARENT, m, v))
    if dest not in certs:
        return None
    cert, name = certs[dest]
    receipt = HERE / f'verification/{name}/receipt.json'
    if not receipt.exists():
        return None
    c, r = json.loads(cert.read_text()), json.loads(receipt.read_text())
    native, python = r.get('runs', {}).get('native'), r.get('runs', {}).get('python')
    native_kunz = name in NATIVE_KUNZ
    if (r.get('status') != 'verified' or native is None or (python is None) != native_kunz
            or type(native.get('states')) is not int or (python is not None and type(python.get('states')) is not int)):
        return None
    ok = (r['certificate_sha256'] == hashlib.sha256(cert.read_bytes()).hexdigest() and c['parent'] == list(PARENT)
          and legal(PARENT, c['opponent_move']) and legal(position((*PARENT, c['opponent_move'])), c['reply'])
          and position((*PARENT, c['opponent_move'], c['reply'])) == dest
          and gcd(*dest) == 1 and list(dest) == c['destination'] == r['position'] and c['destination_outcome'] == 'P'
          and frobenius_number(dest) == c['frobenius'] == r['frobenius']
          and native['states'] == (r38.kunz_states(receipt.parent, dest, c['frobenius']) if native_kunz
                                   else python['states']))
    for solver, run in (('native', native),) + ((() if native_kunz else (('python', python),))):
        files = [receipt.parent / f'{solver}-{stream}.txt' for stream in ('stdout', 'stderr')]
        ok = ok and (run['outcome'] == 'P' and run['returncode'] == 0 and not run['timed_out']
                     and run['frobenius'] == c['frobenius'] and run['command'][-len(dest):] == list(map(str, dest))
                     and all(f.exists() for f in files)
                     and hashlib.sha256(files[0].read_bytes()).hexdigest() == run['stdout_sha256']
                     and hashlib.sha256(files[1].read_bytes()).hexdigest() == run['stderr_sha256'])
        ok = ok and r38.transcript_states(solver, files[0].read_text(), dest, c['frobenius']) == native['states']
    if not ok:
        return None
    return {'evidence': 'finite-witness-native-kunz' if native_kunz else 'finite-witness',
            'destination': key(dest), 'certificate': str(cert.relative_to(ROOT)),
            'receipt': str(receipt.relative_to(ROOT)), 'states': native['states']}


def certified_node(m, v):
    node = next((n for n in NODES if n.name == NODE_ROUTES.get(m)), None)
    if node is None or key((*PARENT, m, v)) != key(node.generators):
        return None
    return {'evidence': 'certified-node', 'destination': key(node.generators),
            'certificate': f'node {node.name} of sylver/short_certificates.py'}


def certified_position(m, v, r38_report):
    name = POSITION_ROUTES.get(m)
    section = r38_report.get(name) if name else None
    if (not section or section.get('outcome') != 'P' or section.get('failures') or r38_report.get('failures')
            or position((*PARENT, m, v)) != tuple(section['position'])):
        return None
    return {'evidence': 'certified-position', 'destination': key(section['position']), 'section': name,
            'certificate': str((R38 / 'audit.json').relative_to(ROOT))}


def search_witness(m, v, hunt):
    row = next((r for r in hunt if r['outcome'] == 'P' and position((*r['child'], r['w'])) == position((*PARENT, m, v))),
               None)
    if row is None:
        return None
    rerun = R38 / f'scan/check_{m}_{v}.out'
    return {'evidence': 'search-witness', 'destination': key((*PARENT, m, v)),
            'search': str((R38 / 'scan/hunt.jsonl').relative_to(ROOT)), 'engine': row.get('engine', 'kunz'),
            'search_states': row['states'], 'rerun': str(rerun.relative_to(ROOT)) if rerun.exists() else None}


def main():
    info = profile(PARENT)
    quiet, recount = r38.coin_sum_obligations(PARENT)
    report = {'position': list(PARENT), 'gcd': info['gcd'], 'tail': info['tail'], 'complete': info['complete'],
              'half_frobenius': info['half_frobenius'], 'obligations': {}, 'failures': []}
    if not (info['complete'] and info['tail'] == 'quiet-end-v1' and quiet):
        report['failures'].append('{16,38,72} is not a short gcd-two position')
    if info['moves'] != recount:
        report['failures'].append('the referee profile and the coin-sum recount disagree')
    if sorted(ROUTES) != info['moves']:
        report['failures'].append('ROUTES does not list exactly the obligations')
    certs = certificates()
    r38_report = json.loads((R38 / 'audit.json').read_text())
    hunt = [json.loads(line) for line in (R38 / 'scan/hunt.jsonl').read_text().splitlines()]
    for m in info['moves']:
        v = ROUTES.get(m)
        if v is None or not (legal(PARENT, m) and legal(position((*PARENT, m)), v)):
            report['failures'].append(f'move {m}: no legal listed reply')
            continue
        row = (finite_witness(m, v, certs) or certified_node(m, v) or certified_position(m, v, r38_report)
               or search_witness(m, v, hunt))
        if row is None:
            report['failures'].append(f'move {m}: the reply {v} has no accepted evidence')
            continue
        report['obligations'][str(m)] = {'reply': v, **row}
    kinds = {}
    for row in report['obligations'].values():
        kinds[row['evidence']] = kinds.get(row['evidence'], 0) + 1
    search_only = [int(m) for m, row in report['obligations'].items() if row['evidence'] == 'search-witness']
    report['summary'] = {'obligations': len(info['moves']), 'certified': len(report['obligations']) - len(search_only),
                         'by_evidence': kinds,
                         'replayed_destinations': len({row['certificate'] for row in report['obligations'].values()
                                                       if row['evidence'].startswith('finite')}),
                         'replayed_states': sum({row['certificate']: row['states'] for row in
                                                 report['obligations'].values()
                                                 if row['evidence'].startswith('finite')}.values())}
    report['search_only'] = search_only
    report['outcome'] = 'P' if not report['failures'] and not search_only else 'unknown'
    print(json.dumps(report, indent=2))
    return 0 if not report['failures'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
