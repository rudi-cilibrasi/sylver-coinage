#!/usr/bin/env python3
"""Coverage audit: every Quiet End obligation of W={16,26,62,98} is N.

W has gcd two and a short (quiet ender) half, so by the Quiet End Theorem it
is P exactly when each of its obligations leads to an N-position: the even
moves 2g for the gaps g of its half, and the odd gaps of the half above 1.
This script lists them twice, with the arena referee's profile
(``sylver.arena.common.profile``) and with an independent coin-sum count,
checks both against the September 22 evidence graph, and accepts exactly
three kinds of evidence per obligation, in this order:

1. ``book``: a certificate recorded in The Book (``sylver/arena/book``) for
   the obligation's position, re-hashed against its digest, with that root,
   outcome N, and the current verifier profile (``book verify`` replays it);
2. ``finite-witness``: a campaign certificate for a reply whose destination
   has gcd one, with a ``verified`` native and Python replay receipt of that
   certificate (outcomes P, matching state counts, return codes, transcripts);
3. ``certified-node``: a winning reply to an infinite P-position certified in
   the repository, either the September 5 release certificate's short cover
   or a node of ``sylver.short_certificates.NODES``.

Nothing else counts: no cache row, native batch, or published position is
accepted directly. The audit fails unless every obligation is covered and
the certified-node evidence is used for exactly the moves in ``NODE_MOVES``
(the claim in RESULT.md). Output: ``python audit.py > audit.json``.
"""
import hashlib
import json
import sys
from math import gcd
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from sylver.arena.common import key, legal, position, profile, sha  # noqa: E402
from sylver.arena.proof import verifier_profile  # noqa: E402
from sylver.short_certificates import NODES  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

W = (16, 26, 62, 98)
NODE_MOVES = {12, 36}
CAMPAIGNS = ROOT / 'sylver/campaigns'
RECORDS = ('w-p-2026-09-27', 'w-one-2026-09-27', 'w-two-2026-09-27', 'w-three-2026-09-27')
GRAPH = CAMPAIGNS / 'w-six-2026-09-22/evidence/proof-graph.json'
BOOK = ROOT / 'sylver/arena/book'
RELEASE = ROOT / 'sylver/publication/plan2-2026-09-05/evidence/certificate.json'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def coin_sum_obligations(p):
    """W's obligations from first principles: gaps of the half by coin sums."""
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


def book_entry(target, index, verifier):
    t = index['targets'].get(target)
    if t is None or t.get('outcome') != 'N':
        return None
    entry = next((e for e in t['entries'] if e['certificate'] == t['record']), None)
    if entry is None or entry.get('outcome') != 'N' or entry.get('verifier') != verifier:
        return None
    path = BOOK / 'certificates' / f"{entry['certificate']}.json"
    if not path.exists() or sha256(path.read_bytes().rstrip(b'\n')) != entry['certificate']:
        return None
    proof = json.loads(path.read_text())
    if proof.get('root') != target or proof['nodes'][target]['outcome'] != 'N':
        return None
    if any(node.get('rule') == 'baseline' for node in proof['nodes'].values()):
        return None   # cites a baseline fact: not self-contained
    return {'evidence': 'book', 'certificate': str(path.relative_to(ROOT)), 'C': entry['C'], 'states': entry['states']}


def finite_witness(m):
    for record in RECORDS:
        d = CAMPAIGNS / record
        cert, receipt = d / f'w{m}-certificate.json', d / f'verification/w{m}/receipt.json'
        if not (cert.exists() and receipt.exists()):
            continue
        c, r = json.loads(cert.read_text()), json.loads(receipt.read_text())
        runs = r.get('runs', {})
        native, python = runs.get('native'), runs.get('python')
        if r.get('status') != 'verified' or native is None or python is None:
            continue
        dest = position((*W, m, c['reply']))
        ok = (r['certificate_sha256'] == sha256(cert.read_bytes()) and c['parent'] == list(W)
              and c['opponent_move'] == m and legal(position((*W, m)), c['reply']) and gcd(*dest) == 1
              and list(dest) == c['destination'] == r['position'] and c['destination_outcome'] == 'P'
              and frobenius_number(dest) == c['frobenius'] == r['frobenius'])
        for name, run in (('native', native), ('python', python)):
            files = [d / f'verification/w{m}/{name}-{stream}.txt' for stream in ('stdout', 'stderr')]
            ok = ok and (run['outcome'] == 'P' and run['returncode'] == 0 and not run['timed_out']
                         and run['frobenius'] == c['frobenius'] and run['command'][-len(dest):] == list(map(str, dest))
                         and all(f.exists() for f in files)
                         and sha256(files[0].read_bytes()) == run['stdout_sha256']
                         and sha256(files[1].read_bytes()) == run['stderr_sha256'])
        if ok and native['states'] == python['states']:
            return {'evidence': 'finite-witness', 'reply': c['reply'], 'destination': key(dest),
                    'certificate': str(cert.relative_to(ROOT)), 'receipt': str(receipt.relative_to(ROOT)),
                    'states': native['states']}
    return None


def certified_node(m, target, graph):
    """A winning reply to an infinite P-position certified in the repository."""
    fact = graph['support'].get(target, {})
    ev = fact.get('evidence', {})
    if fact.get('outcome') != 'N':
        return None
    p = position((*W, m))
    if ev.get('kind') == 'inherited-release-certificate':
        if sha256(RELEASE.read_bytes()) != ev.get('sha256'):
            return None
        facts = json.loads(RELEASE.read_text())['facts']
        f, move = facts.get(target, {}), facts.get(target, {}).get('move')
        dest = facts.get(f.get('destination'), {})
        if (f.get('kind') == 'winning-reply' and f.get('outcome') == 'N' and legal(p, move)
                and key((*p, move)) == f['destination'] and dest.get('kind') == 'short-cover'
                and dest.get('outcome') == 'P'):
            return {'evidence': 'certified-node', 'reply': move, 'destination': f['destination'],
                    'certificate': 'short cover in the September 5 release certificate',
                    'source': str(RELEASE.relative_to(ROOT))}
        return None
    if ev.get('kind') == 'winning-edge':
        move, destination = ev.get('move'), ev.get('destination')
        child = graph['support'].get(destination, {}).get('evidence', {})
        source = child.get('source', '')
        node = next((n for n in NODES if source == f'node:{n.name}'), None)
        if (legal(p, move) and key((*p, move)) == destination and child.get('kind') == 'repository-certificate'
                and node is not None and key(node.generators) == destination):
            return {'evidence': 'certified-node', 'reply': move, 'destination': destination,
                    'certificate': f'node {node.name} of sylver/short_certificates.py',
                    'source': 'sylver/short_certificates.py'}
    return None


def main():
    info = profile(W)
    graph = json.loads(GRAPH.read_text())
    index = json.loads((BOOK / 'index.json').read_text())
    verifier = sha(verifier_profile())
    quiet, recount = coin_sum_obligations(W)
    report = {'position': list(W), 'gcd': info['gcd'], 'tail': info['tail'], 'complete': info['complete'],
              'half_frobenius': info['half_frobenius'], 'obligations': {}, 'failures': []}
    if not (info['complete'] and info['tail'] == 'quiet-end-v1' and quiet):
        report['failures'].append('W is not a short gcd-two position')
    if not info['moves'] == recount == [o['move'] for o in graph['nodes'][key(W)]['obligations']]:
        report['failures'].append('the referee profile, the coin-sum recount, and the evidence graph disagree')
    for m in info['moves']:
        target = key((*W, m))
        row = book_entry(target, index, verifier) or finite_witness(m) or certified_node(m, target, graph)
        if row is None:
            report['failures'].append(f'move {m} has no accepted evidence')
            continue
        report['obligations'][str(m)] = {'destination_of_move': target, **row}
    node_moves = {int(m) for m, row in report['obligations'].items() if row['evidence'] == 'certified-node'}
    if node_moves != NODE_MOVES:
        report['failures'].append(f'certified-node evidence covers {sorted(node_moves)}, expected {sorted(NODE_MOVES)}')
    kinds = {}
    for row in report['obligations'].values():
        kinds[row['evidence']] = kinds.get(row['evidence'], 0) + 1
    report['summary'] = {'obligations': len(info['moves']), 'covered': len(report['obligations']), 'by_evidence': kinds}
    report['outcome'] = 'P' if not report['failures'] else 'unknown'
    print(json.dumps(report, indent=2))
    return 0 if report['outcome'] == 'P' else 1


if __name__ == '__main__':
    raise SystemExit(main())
