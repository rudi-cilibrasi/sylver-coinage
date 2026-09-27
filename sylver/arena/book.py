"""The Book: the best known certificate for each public result.

Every entry is re-verified here in fresh verification runs, never trusting an
episode's own receipt. An entry records canonical bytes C, the verifier's
deterministic evaluated-state count, and the CPU of each run. The entry of
record minimizes the verification-only product (C+100)*(V+1), V the median
run: it prices a proof by what it costs to check, excluding the discovery
cost that tournament scores include; products within 2% are ordered by
fewer states, then fewer bytes. A Book certificate for a public result is an
independent, cheaper-to-check proof of that result, not new mathematics.
"""
from pathlib import Path
from statistics import median
import tempfile

from .common import ROOT, read, sha, write
from .episode import DEFAULT_LIMITS, execution_profile
from .proof import canonical_proof, verifier_profile
from .snapshot import manifest, snapshot

BOOK = ROOT / 'sylver/arena/book'
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
    states = {r['result']['finite_replays'][-1]['cumulative_states'] for r in runs}
    if len(states) != 1:
        raise ValueError('verifier state count differs between runs')
    first = runs[0]['result']; cpu = [r['verification_cpu'] for r in runs]; V = median(cpu)
    return {'certificate': first['certificate_sha256'], 'outcome': first['outcome'], 'C': first['C'],
            'states': states.pop(), 'verification_cpu': cpu, 'V': V, 'product': (first['C'] + 100) * (V + 1),
            'verifier': sha(bundle['manifest']['verifier']), 'execution': sha(bundle['manifest']['execution'])}


def record(entries):
    best = min(e['product'] for e in entries)
    close = [e for e in entries if e['product'] <= best * 1.02]
    return min(close, key=lambda e: (e['states'], e['C'], e['certificate']))['certificate']


def admit(book, proof, entry):
    book = Path(book); (book / 'certificates').mkdir(parents=True, exist_ok=True)
    encoded = canonical_proof(proof, snapshot())
    if sha(encoded) != entry['certificate']:
        raise ValueError('certificate bytes differ from the measured certificate')
    (book / 'certificates' / (entry['certificate'] + '.json')).write_bytes(encoded + b'\n')
    index = read(book / 'index.json') if (book / 'index.json').exists() else {'schema': 1, 'targets': {}}
    target = index['targets'].setdefault(proof['root'], {'outcome': entry['outcome'], 'entries': []})
    if target['outcome'] != entry['outcome']:
        raise ValueError('outcome conflicts with the Book')
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
            ok = (fresh['C'], fresh['states'], fresh['outcome']) == (e['C'], e['states'], target['outcome'])
            report.append({'target': root, 'certificate': e['certificate'], 'ok': ok,
                           'C': fresh['C'], 'states': fresh['states'], 'V': fresh['V']})
    return report


def _rule(proof):
    node = proof['nodes'][proof['root']]
    return f"edge {node['move']}" if node['rule'] == 'edge' else node['rule']


def render_book(book):
    book = Path(book); index = read(book / 'index.json')
    lines = ['# The Book', '',
             'The cheapest-to-check known certificate for each public result. Every entry was re-verified',
             'by the fixed verifier with a fresh memo, three times; *states* is its deterministic',
             'evaluated-state count and *V* the median verification CPU seconds on the recording machine.',
             'The entry of record minimizes (C+100)*(V+1), which prices checking, not discovery.',
             'These are independent certificates of public results, not new mathematics.', '',
             '| Target | Outcome | Proof | C | States | V (s) | (C+100)(V+1) | Entries | Found by |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for root, target in sorted(index['targets'].items(), key=lambda kv: (len(kv[0]), kv[0])):
        e = next(x for x in target['entries'] if x['certificate'] == target['record'])
        proof = read(book / 'certificates' / (e['certificate'] + '.json'))
        found = (e.get('source') or {}).get('competitor') or '—'
        lines.append(f"| `{{{root}}}` | {target['outcome']} | {_rule(proof)} | {e['C']} | {e['states']:,} | "
                     f"{e['V']:.3f} | {e['product']:.0f} | {len(target['entries'])} | {found} |")
    lines += ['', 'Certificates are in `certificates/SHA256.json`; `python -m sylver.arena book verify` replays them.']
    return '\n'.join(lines) + '\n'
