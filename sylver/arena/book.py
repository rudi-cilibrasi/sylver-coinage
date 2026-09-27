"""The Book: the cheapest-to-check known certificate for each public result.

Every entry is re-verified here in fresh verification runs, never trusting an
episode's own receipt, and records canonical bytes C, the verifier's
evaluated-state count (which must agree across runs), and each run's CPU.
The entry of record minimizes the deterministic checking cost
(C+100)*(states/RATE+1): the agreed score's shape with verification time
replaced by the verifier's own work at a fixed RATE, so timing noise never
changes the record. Measured CPU is kept for information. Entries are
compared only under one verifier version. A Book certificate for a public
result is an independent, cheaper-to-check proof of it, not new mathematics.
"""
from pathlib import Path
from statistics import median
import tempfile

from .common import ROOT, read, sha, write
from .episode import DEFAULT_LIMITS, execution_profile
from .proof import canonical_proof, verifier_profile
from .snapshot import manifest, snapshot

BOOK = ROOT / 'sylver/arena/book'
# Verifier states per CPU second: the order of the recording machine's
# measured median (7.6e4-1.2e5 for this Book's first entries). Fixed per Book
# version so the record depends only on C and the deterministic state count.
RATE = 100_000
LIMITS = dict(DEFAULT_LIMITS, cpu_seconds=7200., wall_seconds=14400., memory_mb=16384,
              query_wall_seconds=7200.)


def _bundle(root):
    base = snapshot()
    target = tuple(map(int, root.split(',')))
    return {'manifest': manifest(target, base, verifier_profile(), execution_profile(LIMITS), 'golf',
                                 'The Book: independent re-verification of a public result.'),
            'snapshot': base}


def measure(proof, tools, repeats=3):
    """Replay a certificate ``repeats`` times; the state count must not vary."""
    from .tournament import verify_submission
    bundle = _bundle(proof['root']); runs = []
    with tempfile.TemporaryDirectory() as d:
        for i in range(repeats):
            r = verify_submission(bundle, proof, Path(d) / f'run-{i}', tools)
            if not r['valid']:
                raise ValueError(f"certificate failed re-verification: {r['result'].get('error')}")
            runs.append(r)
    states = {r['result']['finite_replays'][-1]['cumulative_states'] if r['result']['finite_replays'] else 0
              for r in runs}
    if len(states) != 1:
        raise ValueError('verifier state count differs between runs')
    first = runs[0]['result']; cpu = [r['verification_cpu'] for r in runs]
    entry = {'certificate': first['certificate_sha256'], 'outcome': first['outcome'], 'C': first['C'],
             'states': states.pop(), 'verification_cpu': cpu, 'V': median(cpu),
             'verifier': sha(bundle['manifest']['verifier']), 'execution': sha(bundle['manifest']['execution'])}
    entry['cost'] = cost(entry)
    return entry


def cost(entry):
    return (entry['C'] + 100) * (entry['states'] / RATE + 1)


def record(entries):
    return min(entries, key=lambda e: (cost(e), e['states'], e['C'], e['certificate']))['certificate']


def admit(book, proof, entry):
    book = Path(book)
    encoded = canonical_proof(proof, snapshot())
    if sha(encoded) != entry['certificate']:
        raise ValueError('certificate bytes differ from the measured certificate')
    index = read(book / 'index.json') if (book / 'index.json').exists() else {'schema': 1, 'rate': RATE, 'targets': {}}
    target = index['targets'].setdefault(proof['root'], {'outcome': entry['outcome'], 'entries': []})
    if target['outcome'] != entry['outcome']:
        raise ValueError('outcome conflicts with the Book')
    if any(e['verifier'] != entry['verifier'] for e in target['entries']):
        raise ValueError('re-verify this target under the current verifier before adding to it')
    (book / 'certificates').mkdir(parents=True, exist_ok=True)
    (book / 'certificates' / (entry['certificate'] + '.json')).write_bytes(encoded + b'\n')
    target['entries'] = [e for e in target['entries'] if e['certificate'] != entry['certificate']] + [entry]
    target['record'] = record(target['entries'])
    write(book / 'index.json', index)
    return entry


def add_certificate(book, episode, tools, competitor=None, repeats=3):
    """Admit a valid golf episode's certificate after fresh re-verification."""
    episode = Path(episode); receipt = read(episode / 'receipt.json')
    if receipt['status'] != 'valid' or receipt['kind'] != 'golf':
        raise ValueError('only valid golf episodes enter the Book')
    proof = read(episode / 'certificate.json')
    entry = measure(proof, tools, repeats)
    if entry['certificate'] != receipt['verification']['certificate_sha256'] or entry['outcome'] != receipt['outcome']:
        raise ValueError('re-verification disagrees with the episode')
    entry['source'] = {'competitor': competitor, 'task': receipt['task'], 'seed': receipt['seed'],
                       'episode_C': receipt['C'], 'episode_T': receipt['T'], 'episode_S': receipt['S']}
    return admit(book, proof, entry)


def verify_book(book, tools, repeats=1):
    """Replay every certificate; C and states must match their entries exactly."""
    book = Path(book); index = read(book / 'index.json'); report = []
    for root, target in sorted(index['targets'].items()):
        for e in target['entries']:
            proof = read(book / 'certificates' / (e['certificate'] + '.json'))
            fresh = measure(proof, tools, repeats)
            ok = (proof['root'] == root and fresh['certificate'] == e['certificate'] and
                  (fresh['C'], fresh['states'], fresh['outcome']) == (e['C'], e['states'], target['outcome']))
            report.append({'target': root, 'certificate': e['certificate'], 'ok': ok,
                           'C': fresh['C'], 'states': fresh['states'], 'V': fresh['V']})
    return report


def _rule(proof):
    node = proof['nodes'][proof['root']]
    return f"edge {node['move']}" if node['rule'] == 'edge' else node['rule']


def render_book(book):
    book = Path(book); index = read(book / 'index.json')
    rate = index.get('rate', RATE)
    lines = ['# The Book', '',
             'The cheapest-to-check known certificate for each public result. Every entry was re-verified',
             'by the fixed verifier with a fresh memo; *states* is the verifier\'s deterministic',
             'evaluated-state count, identical in every run, and *V* the median verification CPU seconds',
             'on the recording machine (for information). The entry of record minimizes the checking cost',
             f'(C+100)*(states/{rate:,}+1): the agreed score\'s shape with verification time replaced by the',
             'verifier\'s own work, so timing noise never changes the record. These are independent',
             'certificates of public results, not new mathematics.', '',
             '| Target | Outcome | Proof | C | States | V (s) | Checking cost | Entries | Found by |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for root, target in sorted(index['targets'].items(), key=lambda kv: (len(kv[0]), kv[0])):
        e = next(x for x in target['entries'] if x['certificate'] == target['record'])
        proof = read(book / 'certificates' / (e['certificate'] + '.json'))
        found = (e.get('source') or {}).get('competitor') or '—'
        lines.append(f"| `{{{root}}}` | {target['outcome']} | {_rule(proof)} | {e['C']} | {e['states']:,} | "
                     f"{e['V']:.3f} | {cost(e):,.0f} | {len(target['entries'])} | {found} |")
    lines += ['', 'Certificates are in `certificates/SHA256.json`; `python -m sylver.arena book verify` replays them.',
              'How entries are admitted and priced: [sylver/arena/README.md](../README.md#certificate-golf-and-the-book-16).']
    return '\n'.join(lines) + '\n'
