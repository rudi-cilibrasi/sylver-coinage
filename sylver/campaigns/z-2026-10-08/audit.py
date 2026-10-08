#!/usr/bin/env python3
"""Coverage audit of Z={16,30,56} and Z'={16,30,40,44}: both P, so 56 answers 30.

Z is the position after the opening 16, the reply 30 and the answer 56. Z and
Z' have gcd two and short (quiet ender) halves, {8,15,28} and {8,15,20,22}, so
by the Quiet End Theorem each is P exactly when each of its obligations leads
to an N-position: the even moves 2g for the gaps g of its half, and the
half's odd gaps above 1. This script lists them twice, with the arena
referee's profile and with an independent coin-sum count, audits Z' first and
then Z, and accepts exactly these kinds of evidence:

1. ``finite-witness``: a certificate in this directory for a reply whose
   destination has gcd one, with a ``verified`` native and Python replay
   receipt of that certificate (outcomes P, matching state counts, return
   codes, re-hashed transcripts whose own lines state P, the destination's
   Frobenius number and that count);
2. ``certified-node``: the listed winning reply reaches a P-position certified
   in ``sylver.short_certificates.NODES`` (legality and identity checked);
3. ``finite-witness-native-kunz`` (Z's moves 70 and 130 only): as 1, but the
   destination (about 300 and 260 million states) is too large for the Python
   evaluator on this host, so its second replay is ``kunz_solver.cpp``, run
   sequentially (``--threads 1``, the state count native_solver.cpp reports)
   with ``--verify-memo``. The audit requires the exact command, both
   transcripts, the exact source (``KUNZ_SNAPSHOT``, whose hash is pinned
   here), and equal state counts;
4. ``z-prime-is-p`` (Z's move 44 only): the reply 40 reaches Z', which this
   audit has just found P.

The audit fails unless every obligation of both positions is covered.
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
from sylver.arena.common import key, legal, position, profile  # noqa: E402
from sylver.short_certificates import NODES  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

Z = (16, 30, 56)
ZP = (16, 30, 40, 44)
NATIVE_KUNZ = {70, 130}   # Z's witnesses replayed by native_solver.cpp and kunz_solver.cpp
KUNZ_OPTIONS = ['--threads', '1', '--verify-memo', '--verify-threads', '6', '--memo-stats']
# The kunz_solver.cpp the replays ran: main's at 48c1968, kept beside the receipts.
KUNZ_SNAPSHOT = HERE / 'verification/sources/kunz_solver-48c1968.cpp'
KUNZ_SOURCE_SHA256 = '4b6221788c1e76805bbf7d680a493e7c21c9664a2ef3274ff50487302cd2c672'
# (position, certificate prefix, routes to certified nodes: move -> (reply, node))
POSITIONS = {
    "Z'": (ZP, 'zp', {4: (6, 'C'), 6: (4, 'C'), 8: (14, 'E'), 12: (14, 'F'), 14: (8, 'E')}),
    'Z': (Z, 'z', {4: (6, 'C'), 6: (4, 'C'), 8: (14, 'E'), 12: (14, 'F'), 14: (8, 'E'), 20: (8, 'O'),
                   24: (10, 'K')}),
}


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
          and r.get('source') == 'sylver/kunz_solver.cpp' and r.get('command', [None])[1:] == [*KUNZ_OPTIONS, *map(str, dest)]
          and stdout == [f'P winning_move=none frobenius={frobenius} states={states}', f'verified entries={states}']
          and stderr.count(f'kunz_solver: memo verified ({states} entries)') == 1
          and [line.strip() for line in stderr if line.strip().startswith('Exit status')] == ['Exit status: 0'])
    return states if ok else None


def finite_witness(p, prefix, m):
    cert, receipt = HERE / f'{prefix}{m}-certificate.json', HERE / f'verification/{prefix}{m}/receipt.json'
    if not (cert.exists() and receipt.exists()):
        return None
    c, r = json.loads(cert.read_text()), json.loads(receipt.read_text())
    native, python = r.get('runs', {}).get('native'), r.get('runs', {}).get('python')
    native_kunz = p == Z and m in NATIVE_KUNZ
    if (r.get('status') != 'verified' or native is None or (python is None) != native_kunz
            or type(native.get('states')) is not int or (python is not None and type(python.get('states')) is not int)):
        return None
    dest = position((*p, m, c['reply']))
    ok = (r['certificate_sha256'] == hashlib.sha256(cert.read_bytes()).hexdigest() and c['parent'] == list(p)
          and c['opponent_move'] == m and legal(position((*p, m)), c['reply']) and gcd(*dest) == 1
          and list(dest) == c['destination'] == r['position'] and c['destination_outcome'] == 'P'
          and frobenius_number(dest) == c['frobenius'] == r['frobenius']
          and native['states'] == (kunz_states(receipt.parent, dest, c['frobenius']) if native_kunz
                                   else python['states']))
    for name, run in (('native', native),) + ((() if native_kunz else (('python', python),))):
        files = [HERE / f'verification/{prefix}{m}/{name}-{stream}.txt' for stream in ('stdout', 'stderr')]
        ok = ok and (run['outcome'] == 'P' and run['returncode'] == 0 and not run['timed_out']
                     and run['frobenius'] == c['frobenius'] and run['command'][-len(dest):] == list(map(str, dest))
                     and all(f.exists() for f in files)
                     and hashlib.sha256(files[0].read_bytes()).hexdigest() == run['stdout_sha256']
                     and hashlib.sha256(files[1].read_bytes()).hexdigest() == run['stderr_sha256'])
        ok = ok and transcript_states(name, files[0].read_text(), dest, c['frobenius']) == native['states']
    if not ok:
        return None
    return {'evidence': 'finite-witness-native-kunz' if native_kunz else 'finite-witness', 'reply': c['reply'],
            'destination': key(dest),
            'certificate': str(cert.relative_to(ROOT)), 'receipt': str(receipt.relative_to(ROOT)),
            'states': native['states']}


def certified_node(p, routes, m):
    if m not in routes:
        return None
    reply, name = routes[m]
    child = position((*p, m))
    node = next((n for n in NODES if n.name == name), None)
    if node is None or not legal(child, reply) or key((*child, reply)) != key(node.generators):
        return None
    return {'evidence': 'certified-node', 'reply': reply, 'destination': key(node.generators),
            'certificate': f'node {name} of sylver/short_certificates.py', 'source': 'sylver/short_certificates.py'}


def z_prime_is_p(p, m, z_prime_outcome):
    if p != Z or m != 44 or z_prime_outcome != 'P':
        return None
    child = position((*p, m))
    if not legal(child, 40) or position((*child, 40)) != ZP:
        return None
    return {'evidence': 'z-prime-is-p', 'reply': 40, 'destination': key(ZP),
            'certificate': 'the Z\' section of sylver/campaigns/z-2026-10-08/audit.json'}


def audit_position(name, z_prime_outcome=None):
    p, prefix, routes = POSITIONS[name]
    info = profile(p)
    quiet, recount = coin_sum_obligations(p)
    section = {'position': list(p), 'gcd': info['gcd'], 'tail': info['tail'], 'complete': info['complete'],
               'half_frobenius': info['half_frobenius'], 'obligations': {}, 'failures': []}
    if not (info['complete'] and info['tail'] == 'quiet-end-v1' and quiet):
        section['failures'].append(f'{name} is not a short gcd-two position')
    if info['moves'] != recount:
        section['failures'].append(f'{name}: the referee profile and the coin-sum recount disagree')
    for m in info['moves']:
        row = finite_witness(p, prefix, m) or certified_node(p, routes, m) or z_prime_is_p(p, m, z_prime_outcome)
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


def main():
    z_prime = audit_position("Z'")
    z = audit_position('Z', z_prime['outcome'])
    report = {"Z'": z_prime, 'Z': z, 'failures': z_prime['failures'] + z['failures']}
    report['outcome'] = 'P' if z['outcome'] == z_prime['outcome'] == 'P' else 'unknown'
    print(json.dumps(report, indent=2))
    return 0 if report['outcome'] == 'P' else 1


if __name__ == '__main__':
    raise SystemExit(main())
