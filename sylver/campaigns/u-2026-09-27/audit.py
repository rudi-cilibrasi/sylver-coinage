#!/usr/bin/env python3
"""Coverage audit of U={16,26,88}: every Quiet End obligation leads to N, so U is P.

U has gcd two and a short (quiet ender) half, so by the Quiet End Theorem it
is P exactly when each of its obligations leads to an N-position: the even
moves 2g for the gaps g of its half {8,13,44}, and the half's odd gaps above
1. This script lists them twice, with the arena referee's profile and with
an independent coin-sum count, and accepts exactly these kinds of evidence:

1. ``book``: a certificate recorded in The Book for the obligation's
   position, re-hashed against its digest, with that root, outcome N, and the
   current verifier profile (``python -m sylver.arena book verify``);
2. ``finite-witness``: a certificate in this directory for an odd reply whose
   destination has gcd one, with a ``verified`` native and Python replay
   receipt of that certificate (outcomes P, matching state counts, return
   codes, re-hashed transcripts), for a witness too large for The Book's
   verification profile;
3. ``certified-node``: the listed winning reply reaches a P-position certified
   in ``sylver.short_certificates.NODES`` (legality and identity checked);
4. ``w-is-p``: move 98 reaches Q={16,26,88,98}, answered by 62 because
   Q+62 = W={16,26,62,98}, whose own audit
   (``campaigns/w-p-2026-09-27/audit.py``, re-run here) reports P;
5. ``x-is-n``: move 82 reaches X={16,26,82,88}, answered by 701, whose own
   audit (``campaigns/x-2026-10-06/audit.py``, re-run here) reports X N:
   {16,26,82,88,701} is P by two sequential replays with independent move
   code that agree on the exact state count.

Until October 6 move 82 was open and this audit concluded only that U is P
if and only if X is N; ``scan/ledger-x.jsonl`` keeps the sweeps that
refuted X's odd replies up to 687, which X's audit now counts. The audit
fails unless every obligation is covered. Output:
``python audit.py > audit.json``.
"""
import hashlib
import json
import subprocess
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

U = (16, 26, 88)
W = (16, 26, 62, 98)
X = (16, 26, 82, 88)
ROUTES = {8: (20, 'G'), 12: (14, 'F'), 36: (56, 'V'), 56: (36, 'V')}
BOOK = ROOT / 'sylver/arena/book'
W_AUDIT = ROOT / 'sylver/campaigns/w-p-2026-09-27/audit.py'
X_AUDIT = ROOT / 'sylver/campaigns/x-2026-10-06/audit.py'


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


def book_entry(target, index, verifier):
    t = index['targets'].get(target)
    if t is None or t.get('outcome') != 'N':
        return None
    entry = next((e for e in t['entries'] if e['certificate'] == t['record']), None)
    if entry is None or entry.get('outcome') != 'N' or entry.get('verifier') != verifier:
        return None
    path = BOOK / 'certificates' / f"{entry['certificate']}.json"
    if not path.exists() or hashlib.sha256(path.read_bytes().rstrip(b'\n')).hexdigest() != entry['certificate']:
        return None
    proof = json.loads(path.read_text())
    if proof.get('root') != target or proof['nodes'][target]['outcome'] != 'N':
        return None
    if any(node.get('rule') == 'baseline' for node in proof['nodes'].values()):
        return None   # cites a baseline fact: not self-contained
    return {'evidence': 'book', 'certificate': str(path.relative_to(ROOT)), 'C': entry['C'], 'states': entry['states']}


def finite_witness(m):
    cert, receipt = HERE / f'u{m}-certificate.json', HERE / f'verification/u{m}/receipt.json'
    if not (cert.exists() and receipt.exists()):
        return None
    c, r = json.loads(cert.read_text()), json.loads(receipt.read_text())
    native, python = r.get('runs', {}).get('native'), r.get('runs', {}).get('python')
    if r.get('status') != 'verified' or native is None or python is None:
        return None
    dest = position((*U, m, c['reply']))
    ok = (r['certificate_sha256'] == hashlib.sha256(cert.read_bytes()).hexdigest() and c['parent'] == list(U)
          and c['opponent_move'] == m and legal(position((*U, m)), c['reply']) and gcd(*dest) == 1
          and list(dest) == c['destination'] == r['position'] and c['destination_outcome'] == 'P'
          and frobenius_number(dest) == c['frobenius'] == r['frobenius'] and native['states'] == python['states'])
    for name, run in (('native', native), ('python', python)):
        files = [HERE / f'verification/u{m}/{name}-{stream}.txt' for stream in ('stdout', 'stderr')]
        ok = ok and (run['outcome'] == 'P' and run['returncode'] == 0 and not run['timed_out']
                     and run['frobenius'] == c['frobenius'] and run['command'][-len(dest):] == list(map(str, dest))
                     and all(f.exists() for f in files)
                     and hashlib.sha256(files[0].read_bytes()).hexdigest() == run['stdout_sha256']
                     and hashlib.sha256(files[1].read_bytes()).hexdigest() == run['stderr_sha256'])
    if not ok:
        return None
    return {'evidence': 'finite-witness', 'reply': c['reply'], 'destination': key(dest),
            'certificate': str(cert.relative_to(ROOT)), 'receipt': str(receipt.relative_to(ROOT)),
            'states': native['states']}


def certified_node(m):
    if m not in ROUTES:
        return None
    reply, name = ROUTES[m]
    p = position((*U, m))
    node = next((n for n in NODES if n.name == name), None)
    if node is None or not legal(p, reply) or key((*p, reply)) != key(node.generators):
        return None
    return {'evidence': 'certified-node', 'reply': reply, 'destination': key(node.generators),
            'certificate': f'node {name} of sylver/short_certificates.py', 'source': 'sylver/short_certificates.py'}


def w_is_p(m, w_outcome):
    p = position((*U, m))
    if w_outcome != 'P' or not legal(p, 62) or position((*p, 62)) != W:
        return None
    return {'evidence': 'w-is-p', 'reply': 62, 'destination': key(W),
            'certificate': 'sylver/campaigns/w-p-2026-09-27/audit.json'}


def x_is_n(m, x_report):
    p = position((*U, m))
    if (p != X or x_report.get('position') != list(X) or x_report.get('outcome') != 'N'
            or x_report.get('failures') != [] or x_report.get('destination_outcome') != 'P'):
        return None
    reply = x_report.get('reply')
    if not isinstance(reply, int) or not legal(p, reply) or x_report.get('destination') != key((*p, reply)):
        return None
    states = {run['states'] for run in x_report['replays'].values()}
    return {'evidence': 'x-is-n', 'reply': reply, 'destination': x_report['destination'],
            'certificate': 'sylver/campaigns/x-2026-10-06/audit.json', 'states': states.pop()}


def main():
    info = profile(U)
    quiet, recount = coin_sum_obligations(U)
    index = json.loads((BOOK / 'index.json').read_text())
    verifier = sha(verifier_profile())
    w_run = subprocess.run([sys.executable, str(W_AUDIT)], capture_output=True, text=True)
    w_report = json.loads(w_run.stdout) if w_run.stdout.strip() else {}
    w_outcome = 'unknown'
    if (w_run.returncode == 0 and w_report.get('position') == list(W) and w_report.get('outcome') == 'P'
            and w_report['summary']['covered'] == w_report['summary']['obligations'] == 52):
        w_outcome = 'P'
    x_run = subprocess.run([sys.executable, str(X_AUDIT)], capture_output=True, text=True)
    x_report = json.loads(x_run.stdout) if x_run.returncode == 0 and x_run.stdout.strip() else {}
    report = {'position': list(U), 'gcd': info['gcd'], 'tail': info['tail'], 'complete': info['complete'],
              'half_frobenius': info['half_frobenius'], 'W_audit_outcome': w_outcome,
              'X_audit_outcome': x_report.get('outcome', 'unknown'), 'obligations': {}, 'failures': []}
    if not (info['complete'] and info['tail'] == 'quiet-end-v1' and quiet):
        report['failures'].append('U is not a short gcd-two position')
    if info['moves'] != recount:
        report['failures'].append('the referee profile and the coin-sum recount disagree')
    for m in info['moves']:
        target = key((*U, m))
        row = (book_entry(target, index, verifier) or finite_witness(m) or certified_node(m)
               or w_is_p(m, w_outcome) or x_is_n(m, x_report))
        if row is None:
            report['failures'].append(f'move {m} has no accepted evidence')
            continue
        report['obligations'][str(m)] = {'destination_of_move': target, **row}
    kinds = {}
    for row in report['obligations'].values():
        kinds[row['evidence']] = kinds.get(row['evidence'], 0) + 1
    report['summary'] = {'obligations': len(info['moves']), 'covered': len(report['obligations']),
                         'by_evidence': kinds}
    if len(report['obligations']) != len(info['moves']):
        report['failures'].append('not every obligation is covered')
    report['outcome'] = 'P' if not report['failures'] else 'unknown'
    print(json.dumps(report, indent=2))
    return 0 if not report['failures'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
