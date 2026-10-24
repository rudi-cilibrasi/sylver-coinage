#!/usr/bin/env python3
"""The P-position Q={16,20,46}, and the answers to the reply 40 after the opening 16 it and others refute.

(Q is on Sicherman's list of P-positions; see the record.)

Q has gcd two and a short (quiet ender) half, {8,10,23}. So by the Quiet End
Theorem it is P exactly when each of its obligations leads to an N-position:
the even moves 2g for the gaps g of its half, and the half's odd gaps above 1.
The audit lists them twice, with the arena referee's profile and with an
independent coin-sum count, and accepts exactly these kinds of evidence for an
obligation m:

1. ``finite-witness``: a certificate in this directory for a reply whose
   destination has gcd one, with a ``verified`` native and Python replay
   receipt of that certificate (outcomes P, matching state counts, return
   codes, re-hashed transcripts whose own lines state P, the destination's
   Frobenius number and that count);
2. ``certified-node``: the listed reply reaches a P-position certified in
   ``sylver.short_certificates.NODES`` (legality and identity checked).

The audit fails unless every obligation is covered. It then checks the
refutations: for each answer a in REFUTED, {16,40,a} is N because a listed
move reaches a P-position: a finite witness (a certificate with parent
{16,40}, replayed the same way), a certified node, Q, B28={16,28,38,40} or
Z'={16,30,40,44}. The reply-38 and Z records certify B28 and Z'; their own
audits are run here for those two positions. So a does not answer the reply
40. Output: ``python audit.py > audit.json``.
"""
import hashlib
import importlib.util
import json
import sys
from math import gcd
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from sylver.arena.common import key, legal, position, profile  # noqa: E402
from sylver.short_certificates import NODES  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

OPENING, REPLY = 16, 40
# name: (generators, certificate prefix, node routes {move: (reply, node)})
POSITIONS = {
    'Q': ((16, 20, 46), 'q', {4: (6, 'C'), 6: (4, 'C'), 8: (26, 'G'), 14: (26, 'R'), 26: (8, 'G'), 30: (8, 'O')}),
}
# positions another record certifies: name -> (generators, that record's audit)
EXTERNAL = {'B28': ((16, 28, 38, 40), HERE.parent / 'r38-2026-10-09' / 'audit.py'),
            "Z'": ((16, 30, 40, 44), HERE.parent / 'z-2026-10-08' / 'audit.py')}
# answer a to the reply 40: (the move that takes {16,40,a} to a P-position, and how that position is known P)
REFUTED = {2: (3, 'finite'), 4: (6, 'C'), 6: (4, 'C'), 8: (14, 'E'), 10: (9, 'finite'), 12: (14, 'F'),
           14: (8, 'E'), 18: (5, 'finite'), 20: (34, 'T'), 22: (12, 'P0'), 24: (10, 'K'), 26: (11, 'finite'),
           28: (38, 'B28'), 30: (17, 'finite'), 34: (20, 'T'), 38: (28, 'B28'), 42: (23, 'finite'),
           44: (30, "Z'"), 46: (20, 'Q'), 50: (11, 'finite'), 70: (37, 'finite')}
REFUTATION_PREFIX = 'r40_'


def coin_sum_obligations(p):
    """The obligations from first principles: gaps of the half by coin sums."""
    half = [g // 2 for g in p]
    limit = 2 * max(half) * min(half)
    reach = [True] + [False] * limit
    for n in range(1, limit + 1):
        reach[n] = any(g <= n and reach[n - g] for g in half)
    gaps = [n for n in range(1, limit + 1) if not reach[n]]
    top = gaps[-1]
    # every number above top is reachable: a run of min(half) reachable numbers follows it
    assert limit - top >= min(half) and all(reach[n] for n in range(top + 1, limit + 1))
    quiet = all((x in gaps) != ((top - x) in gaps) for x in range(top + 1))
    return quiet, sorted([2 * g for g in gaps] + [g for g in gaps if g > 1 and g % 2])


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


def finite_witness(p, prefix, m):
    """A verified certificate that p+m is N by a reply reaching a finite P-position, or None."""
    cert, receipt = HERE / f'{prefix}{m}-certificate.json', HERE / f'verification/{prefix}{m}/receipt.json'
    if not (cert.exists() and receipt.exists()):
        return None
    c, r = json.loads(cert.read_text()), json.loads(receipt.read_text())
    native, python = r.get('runs', {}).get('native'), r.get('runs', {}).get('python')
    if (r.get('status') != 'verified' or native is None or python is None
            or type(native.get('states')) is not int or type(python.get('states')) is not int):
        return None
    dest = position((*p, m, c['reply']))
    ok = (r['certificate_sha256'] == hashlib.sha256(cert.read_bytes()).hexdigest() and c['parent'] == list(p)
          and c['opponent_move'] == m and legal(position(p), m) and legal(position((*p, m)), c['reply'])
          and gcd(*dest) == 1 and list(dest) == c['destination'] == r['position'] and c['destination_outcome'] == 'P'
          and frobenius_number(dest) == c['frobenius'] == r['frobenius'] and native['states'] == python['states'])
    for solver, run in (('native', native), ('python', python)):
        files = [HERE / f'verification/{prefix}{m}/{solver}-{stream}.txt' for stream in ('stdout', 'stderr')]
        ok = ok and (run['outcome'] == 'P' and run['returncode'] == 0 and not run['timed_out']
                     and run['frobenius'] == c['frobenius'] and run['command'][-len(dest):] == list(map(str, dest))
                     and all(f.exists() for f in files)
                     and hashlib.sha256(files[0].read_bytes()).hexdigest() == run['stdout_sha256']
                     and hashlib.sha256(files[1].read_bytes()).hexdigest() == run['stderr_sha256'])
        ok = ok and transcript_states(solver, files[0].read_text(), dest, c['frobenius']) == native['states']
    if not ok:
        return None
    return {'evidence': 'finite-witness', 'reply': c['reply'], 'destination': key(dest),
            'certificate': str(cert.relative_to(ROOT)), 'receipt': str(receipt.relative_to(ROOT)),
            'states': native['states']}


def certified_node(p, routes, m):
    if m not in routes:
        return None
    reply, node_name = routes[m]
    child = position((*p, m))
    node = next((n for n in NODES if n.name == node_name), None)
    if node is None or not legal(child, reply) or key((*child, reply)) != key(node.generators):
        return None
    return {'evidence': 'certified-node', 'reply': reply, 'destination': key(node.generators),
            'certificate': f'node {node_name} of sylver/short_certificates.py', 'source': 'sylver/short_certificates.py'}


def audit_position(name):
    generators, prefix, node_routes = POSITIONS[name]
    p = position(generators)
    info = profile(p)
    quiet, recount = coin_sum_obligations(p)
    section = {'position': list(p), 'gcd': info['gcd'], 'tail': info['tail'], 'complete': info['complete'],
               'half_frobenius': info['half_frobenius'], 'obligations': {}, 'failures': []}
    if not (info['complete'] and info['tail'] == 'quiet-end-v1' and quiet):
        section['failures'].append(f'{name} is not a short gcd-two position')
    if info['moves'] != recount:
        section['failures'].append(f'{name}: the referee profile and the coin-sum recount disagree')
    for m in info['moves']:
        row = finite_witness(p, prefix, m) or certified_node(p, node_routes, m)
        if row is None:
            section['failures'].append(f'{name}: move {m} has no accepted evidence')
            continue
        section['obligations'][str(m)] = {'destination_of_move': key((*p, m)), **row}
    kinds = {}
    for row in section['obligations'].values():
        kinds[row['evidence']] = kinds.get(row['evidence'], 0) + 1
    section['summary'] = {'obligations': len(info['moves']), 'covered': len(section['obligations']),
                          'by_evidence': kinds,
                          'replayed_states': sum(row.get('states', 0) for row in section['obligations'].values())}
    if len(section['obligations']) != len(info['moves']):
        section['failures'].append(f'{name}: not every obligation is covered')
    section['outcome'] = 'P' if not section['failures'] else 'unknown'
    return section


def audit_external(name):
    """A position by its own record's audit (that record's certificates, in its directory)."""
    generators, path = EXTERNAL[name]
    spec = importlib.util.spec_from_file_location(f'audit_{path.parent.name}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    section = module.audit_position(name, {}) if name == 'B28' else module.audit_position(name)
    failures = list(section['failures'])
    if section['position'] != list(position(generators)):
        failures.append(f'{name}: that audit checked {section["position"]}, not {list(position(generators))}')
    return {'position': section['position'], 'outcome': section['outcome'] if not failures else 'unknown',
            'summary': section['summary'], 'failures': failures, 'audit': str(path.relative_to(ROOT))}


def refutations(known):
    """For each answer a in REFUTED: its move reaches a P-position, so {16,40,a} is N."""
    rows, failures = {}, []
    base = position((OPENING, REPLY))
    for a, (move, route) in REFUTED.items():
        candidate = position((OPENING, REPLY, a))
        ok = legal((OPENING,), REPLY) and legal(base, a) and legal(candidate, move)
        row = {'position': key(candidate), 'move': move, 'destination': key((*candidate, move)), 'route': route}
        if route == 'finite':
            witness = finite_witness(base, REFUTATION_PREFIX, a)
            ok = ok and witness is not None and witness['reply'] == move
            if witness:
                row.update(certificate=witness['certificate'], receipt=witness['receipt'], states=witness['states'])
        elif route in known:
            ok = ok and known[route][1] and position((*candidate, move)) == position(known[route][0])
        else:
            node = next((n for n in NODES if n.name == route), None)
            ok = ok and node is not None and key((*candidate, move)) == key(node.generators)
            row['certificate'] = f'node {route} of sylver/short_certificates.py'
        row['outcome'] = 'N' if ok else 'unknown'
        rows[str(a)] = row
        if not ok:
            failures.append(f'answer {a}: the move {move} does not reach a position shown P')
    return rows, failures


def main():
    report = {name: audit_position(name) for name in POSITIONS}
    report.update({name: audit_external(name) for name in EXTERNAL})
    known = {name: (POSITIONS[name][0], report[name]['outcome'] == 'P') for name in POSITIONS}
    known.update({name: (EXTERNAL[name][0], report[name]['outcome'] == 'P') for name in EXTERNAL})
    report['refuted_answers_to_40'], refutation_failures = refutations(known)
    report['failures'] = [f for name in (*POSITIONS, *EXTERNAL) for f in report[name]['failures']] + refutation_failures
    report['verdict'] = 'verified' if not report['failures'] else 'failed'   # Q, B28, Z' and every refutation
    print(json.dumps(report, indent=2))
    return 0 if not report['failures'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
