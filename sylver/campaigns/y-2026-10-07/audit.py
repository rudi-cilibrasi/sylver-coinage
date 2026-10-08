#!/usr/bin/env python3
"""Coverage audit of Y={16,28,58}: every Quiet End obligation leads to N, so Y is P.

Y is the position after the opening 16, the reply 28 and the answer 58. Y has
gcd two and a short (quiet ender) half, {8,14,29}, so by the Quiet End Theorem
it is P exactly when each of its obligations leads to an N-position: the even
moves 2g for the gaps g of its half, and the half's odd gaps above 1. This
script lists them twice, with the arena referee's profile and with an
independent coin-sum count, and accepts exactly these kinds of evidence:

1. ``finite-witness``: a certificate in this directory for a reply whose
   destination has gcd one, with a ``verified`` native and Python replay
   receipt of that certificate (outcomes P, matching state counts, return
   codes, re-hashed transcripts whose own lines state P, the destination's
   Frobenius number and that count);
2. ``certified-node``: the listed winning reply reaches a P-position certified
   in ``sylver.short_certificates.NODES`` (legality and identity checked).

The audit fails unless every obligation is covered. Y P means that 58
answers 28 after the opening 16. Output: ``python audit.py > audit.json``.
"""
import hashlib
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

Y = (16, 28, 58)
ROUTES = {4: (6, 'C'), 6: (4, 'C'), 8: (14, 'E'), 12: (14, 'F'), 14: (8, 'E'), 22: (12, 'P0')}


def coin_sum_obligations(p):
    """The obligations from first principles: gaps of the half by coin sums."""
    half = [g // 2 for g in p]
    limit = 2 * max(half) * min(half)
    reach = [True] + [False] * limit
    for n in range(1, limit + 1):
        reach[n] = any(g <= n and reach[n - g] for g in half)
    gaps = [n for n in range(1, limit + 1) if not reach[n]]
    top = gaps[-1]
    assert all(reach[n] for n in range(top + 1, limit + 1))
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
    ok = row.get('position') == list(dest) and row.get('outcome') == 'P' and row.get('frobenius') == frobenius
    return row.get('states') if ok else None


def finite_witness(m):
    cert, receipt = HERE / f'y{m}-certificate.json', HERE / f'verification/y{m}/receipt.json'
    if not (cert.exists() and receipt.exists()):
        return None
    c, r = json.loads(cert.read_text()), json.loads(receipt.read_text())
    native, python = r.get('runs', {}).get('native'), r.get('runs', {}).get('python')
    if r.get('status') != 'verified' or native is None or python is None:
        return None
    dest = position((*Y, m, c['reply']))
    ok = (r['certificate_sha256'] == hashlib.sha256(cert.read_bytes()).hexdigest() and c['parent'] == list(Y)
          and c['opponent_move'] == m and legal(position((*Y, m)), c['reply']) and gcd(*dest) == 1
          and list(dest) == c['destination'] == r['position'] and c['destination_outcome'] == 'P'
          and frobenius_number(dest) == c['frobenius'] == r['frobenius'] and native['states'] == python['states'])
    for name, run in (('native', native), ('python', python)):
        files = [HERE / f'verification/y{m}/{name}-{stream}.txt' for stream in ('stdout', 'stderr')]
        ok = ok and (run['outcome'] == 'P' and run['returncode'] == 0 and not run['timed_out']
                     and run['frobenius'] == c['frobenius'] and run['command'][-len(dest):] == list(map(str, dest))
                     and all(f.exists() for f in files)
                     and hashlib.sha256(files[0].read_bytes()).hexdigest() == run['stdout_sha256']
                     and hashlib.sha256(files[1].read_bytes()).hexdigest() == run['stderr_sha256'])
        # The transcripts themselves must state the result, not only the receipt.
        ok = ok and transcript_states(name, files[0].read_text(), dest, c['frobenius']) == native['states']
    if not ok:
        return None
    return {'evidence': 'finite-witness', 'reply': c['reply'], 'destination': key(dest),
            'certificate': str(cert.relative_to(ROOT)), 'receipt': str(receipt.relative_to(ROOT)),
            'states': native['states']}


def certified_node(m):
    if m not in ROUTES:
        return None
    reply, name = ROUTES[m]
    p = position((*Y, m))
    node = next((n for n in NODES if n.name == name), None)
    if node is None or not legal(p, reply) or key((*p, reply)) != key(node.generators):
        return None
    return {'evidence': 'certified-node', 'reply': reply, 'destination': key(node.generators),
            'certificate': f'node {name} of sylver/short_certificates.py', 'source': 'sylver/short_certificates.py'}


def main():
    info = profile(Y)
    quiet, recount = coin_sum_obligations(Y)
    report = {'position': list(Y), 'gcd': info['gcd'], 'tail': info['tail'], 'complete': info['complete'],
              'half_frobenius': info['half_frobenius'], 'obligations': {}, 'failures': []}
    if not (info['complete'] and info['tail'] == 'quiet-end-v1' and quiet):
        report['failures'].append('Y is not a short gcd-two position')
    if info['moves'] != recount:
        report['failures'].append('the referee profile and the coin-sum recount disagree')
    for m in info['moves']:
        row = finite_witness(m) or certified_node(m)
        if row is None:
            report['failures'].append(f'move {m} has no accepted evidence')
            continue
        report['obligations'][str(m)] = {'destination_of_move': key((*Y, m)), **row}
    kinds = {}
    for row in report['obligations'].values():
        kinds[row['evidence']] = kinds.get(row['evidence'], 0) + 1
    report['summary'] = {'obligations': len(info['moves']), 'covered': len(report['obligations']),
                         'by_evidence': kinds,
                         'replayed_states': sum(row.get('states', 0) for row in report['obligations'].values())}
    if len(report['obligations']) != len(info['moves']):
        report['failures'].append('not every obligation is covered')
    report['outcome'] = 'P' if not report['failures'] else 'unknown'
    print(json.dumps(report, indent=2))
    return 0 if not report['failures'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
