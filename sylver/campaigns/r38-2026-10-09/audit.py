#!/usr/bin/env python3
"""Four new P-positions after the opening 16, and the answers to the reply 38 they refute.

I={16,20,22,24}, B28={16,28,38,40}, B24={16,24,38,44} and B56={16,38,56,60}
each have gcd two and a short (quiet ender) half. So by the Quiet End Theorem each is P exactly when
each of its obligations leads to an N-position: the even moves 2g for the gaps
g of its half, and the half's odd gaps above 1. The audit lists them twice,
with the arena referee's profile and with an independent coin-sum count,
audits the positions in the listed order, and accepts exactly these kinds of
evidence for an obligation m:

1. ``finite-witness``: a certificate in this directory for a reply whose
   destination has gcd one, with a ``verified`` native and Python replay
   receipt of that certificate (outcomes P, matching state counts, return
   codes, re-hashed transcripts whose own lines state P, the destination's
   Frobenius number and that count);
2. ``finite-witness-native-kunz`` (the moves in NATIVE_KUNZ only): as 1, but
   the destination (above 175 million states) gets a ``kunz_solver.cpp``
   replay in place of the Python one, run sequentially (``--threads 1``, the
   state count native_solver.cpp reports) with ``--verify-memo``. The audit
   requires the exact command, both transcripts, the exact source
   (KUNZ_SNAPSHOT, whose hash is pinned here), and equal state counts;
3. ``certified-node``: the listed reply reaches a P-position certified in
   ``sylver.short_certificates.NODES`` (legality and identity checked);
4. ``nested-p``: the listed reply reaches another position of POSITIONS that
   this audit has already found P (it must be listed earlier).

The audit fails unless every obligation of every position is covered. It then
checks the refutations: for each answer a in REFUTED, the listed move takes
{16,38,a} to one of these P-positions or to a certified node, so {16,38,a}
is N and a does not answer the reply 38. Output: ``python audit.py > audit.json``.
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

OPENING, REPLY = 16, 38
# name: (generators, certificate prefix, node routes {move: (reply, node)}, nested routes {move: (reply, name)}),
# audited in this order
POSITIONS = {
    'I': ((16, 20, 22, 24), 'i', {4: (6, 'C'), 6: (4, 'C'), 12: (26, 'D'), 26: (12, 'D')}, {}),
    'B28': ((16, 28, 38, 40), 'b28_', {4: (6, 'C'), 6: (4, 'C'), 8: (14, 'E'), 12: (14, 'F'), 14: (8, 'E'),
                                       20: (26, 'J'), 22: (12, 'P0'), 26: (20, 'J')}, {}),
    'B24': ((16, 24, 38, 44), 'b24_', {4: (6, 'C'), 6: (4, 'C'), 8: (14, 'E'), 12: (14, 'F'), 14: (8, 'E'),
                                       22: (12, 'P0')}, {20: (22, 'I')}),
    'B56': ((16, 38, 56, 60), 'b56_', {4: (6, 'C'), 6: (4, 'C'), 8: (14, 'E'), 12: (14, 'F'), 14: (8, 'E'),
                                       22: (12, 'P0')},
            {24: (44, 'B24'), 28: (40, 'B28'), 40: (28, 'B28'), 44: (24, 'B24')}),
}
# B56's four witnesses above 175 million states: native_solver.cpp and sequential kunz_solver.cpp replays
NATIVE_KUNZ = {'B56': {74, 84, 90, 122}}
KUNZ_OPTIONS = ['--threads', '1', '--verify-memo', '--verify-threads', '6', '--memo-stats']
KUNZ_SNAPSHOT = HERE / 'verification/sources/kunz_solver-243866d.cpp'
KUNZ_SOURCE_SHA256 = '4b6221788c1e76805bbf7d680a493e7c21c9664a2ef3274ff50487302cd2c672'   # unchanged since 48c1968
# answer a to the reply 38: (the move that takes {16,38,a} to a P-position, that position or certified node)
REFUTED = {4: (6, 'C'), 6: (4, 'C'), 8: (14, 'E'), 12: (14, 'F'), 14: (8, 'E'), 22: (12, 'P0'),
           24: (44, 'B24'), 28: (40, 'B28'), 40: (28, 'B28'), 44: (24, 'B24'), 56: (60, 'B56')}


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
          and [line.strip() for line in stderr if line.strip().startswith('Exit status')] == ['Exit status: 0']
          and timed_arguments(stderr) == [*KUNZ_OPTIONS, *map(str, dest)])
    return states if ok else None


def timed_arguments(stderr):
    """The arguments (after the binary) of the one command /usr/bin/time reports in a transcript, or None."""
    timed = [line.strip() for line in stderr if line.strip().startswith('Command being timed: "')]
    if len(timed) != 1 or not timed[0].endswith('"'):
        return None
    return timed[0][len('Command being timed: "'):-1].split()[1:]


def finite_witness(name, p, prefix, m):
    cert, receipt = HERE / f'{prefix}{m}-certificate.json', HERE / f'verification/{prefix}{m}/receipt.json'
    if not (cert.exists() and receipt.exists()):
        return None
    c, r = json.loads(cert.read_text()), json.loads(receipt.read_text())
    native, python = r.get('runs', {}).get('native'), r.get('runs', {}).get('python')
    native_kunz = m in NATIVE_KUNZ.get(name, ())
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
    for solver, run in (('native', native),) + ((() if native_kunz else (('python', python),))):
        files = [HERE / f'verification/{prefix}{m}/{solver}-{stream}.txt' for stream in ('stdout', 'stderr')]
        ok = ok and (run['outcome'] == 'P' and run['returncode'] == 0 and not run['timed_out']
                     and run['frobenius'] == c['frobenius'] and run['command'][-len(dest):] == list(map(str, dest))
                     and all(f.exists() for f in files)
                     and hashlib.sha256(files[0].read_bytes()).hexdigest() == run['stdout_sha256']
                     and hashlib.sha256(files[1].read_bytes()).hexdigest() == run['stderr_sha256'])
        ok = ok and transcript_states(solver, files[0].read_text(), dest, c['frobenius']) == native['states']
    if not ok:
        return None
    return {'evidence': 'finite-witness-native-kunz' if native_kunz else 'finite-witness', 'reply': c['reply'],
            'destination': key(dest),
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


def nested_p(p, routes, m, outcomes):
    if m not in routes:
        return None
    reply, target_name = routes[m]
    target = position(POSITIONS[target_name][0])
    child = position((*p, m))
    if outcomes.get(target_name) != 'P' or not legal(child, reply) or position((*child, reply)) != target:
        return None
    return {'evidence': 'nested-p', 'reply': reply, 'destination': key(target), 'section': target_name,
            'certificate': str((HERE / 'RESULT.md').relative_to(ROOT))}


def audit_position(name, outcomes):
    generators, prefix, node_routes, nested_routes = POSITIONS[name]
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
        row = (finite_witness(name, p, prefix, m) or certified_node(p, node_routes, m)
               or nested_p(p, nested_routes, m, outcomes))
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


def target_of(name, outcomes):
    """The position named ``name`` (one of POSITIONS, or a certified node) and whether it is known P."""
    if name in POSITIONS:
        return position(POSITIONS[name][0]), outcomes.get(name) == 'P'
    node = next((n for n in NODES if n.name == name), None)
    return (position(node.generators), True) if node else (None, False)


def refutations(outcomes):
    """For each answer a in REFUTED: its move reaches a P-position, so {16,38,a} is N."""
    rows, failures = {}, []
    for a, (move, name) in REFUTED.items():
        candidate = position((OPENING, REPLY, a))
        target, target_p = target_of(name, outcomes)
        ok = (target is not None and target_p and legal((OPENING,), REPLY) and legal(position((OPENING, REPLY)), a)
              and legal(candidate, move) and position((*candidate, move)) == target)
        rows[str(a)] = {'position': key(candidate), 'move': move, 'reaches': name,
                        'destination': key(target) if target is not None else None,
                        'outcome': 'N' if ok else 'unknown'}
        if not ok:
            failures.append(f'answer {a}: the move {move} does not reach a position found P')
    return rows, failures


def main():
    report, outcomes = {}, {}
    for name in POSITIONS:
        report[name] = audit_position(name, outcomes)
        outcomes[name] = report[name]['outcome']
    report['refuted_answers_to_38'], refutation_failures = refutations(outcomes)
    report['failures'] = [f for name in POSITIONS for f in report[name]['failures']] + refutation_failures
    report['outcome'] = 'P' if all(o == 'P' for o in outcomes.values()) else 'unknown'   # of every listed position
    print(json.dumps(report, indent=2))
    return 0 if not report['failures'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
