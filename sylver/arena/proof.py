"""Fixed proof language, canonical byte accounting, and fresh finite replay."""
from math import gcd
from pathlib import Path

from .common import ROOT, SCHEMA, canonical, fields, from_key, key, legal, position, profile, sha
from .snapshot import validate_snapshot


def verifier_profile():
    paths = ['sylver/arena/proof.py', 'sylver/arena/common.py', 'sylver/arena/snapshot.py',
             'sylver/arena/exact.py', 'sylver/arena/worker.py',
             'sylver/solver.py', 'sylver/short_certificates.py', 'sylver/native_solver.cpp']
    return {'schema': SCHEMA, 'finite': 'native-shared-fresh-frobenius-order-v1',
            'native_words': 16, 'max_frobenius': 1023,
            'sources': {p: sha((ROOT / p).read_bytes()) for p in paths}}


def canonical_proof(proof, baseline, target=None):
    """Check the whole structure, then strip unreachable nodes before pricing.

    Unsupported or malformed unreachable nodes are rejected too. Timing/logs
    live outside this closed proof schema and cannot carry dependencies.
    """
    validate_snapshot(baseline)
    fields(proof, ('schema', 'root', 'nodes'))
    if type(proof['schema']) is not int or proof['schema'] != SCHEMA or not isinstance(proof['nodes'], dict):
        raise ValueError('invalid proof schema')
    root = proof['root']
    from_key(root)
    if target is not None and key(target) != root:
        raise ValueError('proof classifies a different target')
    if not proof['nodes'] or len(proof['nodes']) > 10000:
        raise ValueError('invalid proof size')
    nodes = {}
    for k, node in proof['nodes'].items():
        p = from_key(k)
        if not isinstance(node, dict) or node.get('outcome') not in ('P', 'N'):
            raise ValueError('unknown is not a proof')
        rule = node.get('rule')
        extras = {'finite': (), 'baseline': ('fact',), 'edge': ('move', 'child'),
                  'cover': ('tail', 'children')}
        if rule not in extras:
            raise ValueError('unsupported proof rule')
        fields(node, ('outcome', 'rule', *extras[rule]))
        n = dict(node)
        if rule == 'finite':
            if gcd(*p) != 1 or profile(p)['frobenius'] > 1023:
                raise ValueError('unsupported finite leaf')
        elif rule == 'baseline':
            f = baseline['facts'].get(n['fact'])
            if f is None or f['position'] != list(p) or f['outcome'] != n['outcome']:
                raise ValueError('unpermitted baseline reference')
        elif rule == 'edge':
            if n['outcome'] != 'N' or not legal(p, n['move']) or key((*p, n['move'])) != n['child']:
                raise ValueError('illegal winning edge or semigroup identity')
        elif rule == 'cover':
            info = profile(p)
            if (n['outcome'] != 'P' or not info['complete'] or n['tail'] != info['tail']
                    or n['tail'] != 'finite' and n['tail'] not in baseline['theorems']):
                raise ValueError('unsupported infinite tail or P claim')
            if not isinstance(n['children'], list):
                raise ValueError('expected child list')
            for row in n['children']:
                fields(row, ('move', 'child'))
                if not legal(p, row['move']) or key((*p, row['move'])) != row['child']:
                    raise ValueError('illegal cover edge')
            n['children'] = sorted(n['children'], key=lambda r: r['move'])
            if [r['move'] for r in n['children']] != info['moves']:
                raise ValueError('incomplete or duplicate legal move coverage')
        nodes[k] = n
    visited, active = set(), set()
    def visit(k):
        if k in active:
            raise ValueError('circular proof')
        if k in visited:
            return
        if k not in nodes:
            raise ValueError('missing transitive proof dependency')
        active.add(k)
        n = nodes[k]
        children = ([n['child']] if n['rule'] == 'edge' else
                    [r['child'] for r in n['children']] if n['rule'] == 'cover' else [])
        expected = 'P' if n['rule'] == 'edge' else 'N'
        for child in children:
            if child not in nodes or nodes[child]['outcome'] != expected:
                raise ValueError('wrong child outcome')
            visit(child)
        active.remove(k)
        visited.add(k)
    # Validate unreachable support too; only reachable valid nodes count in C.
    for k in nodes:
        visit(k)
    visited.clear()
    visit(root)
    result = {'schema': SCHEMA, 'root': root, 'nodes': {k: nodes[k] for k in sorted(visited)}}
    return canonical(result)


def verify(proof, baseline, target, exact_batch):
    """exact_batch is the trusted, accounted runner; it never loads a cache."""
    import json
    encoded = canonical_proof(proof, baseline, target)
    data = json.loads(encoded)
    finite = sorted((from_key(k) for k, n in data['nodes'].items() if n['rule'] == 'finite'),
                    key=lambda p: (profile(p)['frobenius'], key(p)))
    replays = exact_batch(finite) if finite else []
    if len(replays) != len(finite):
        raise ValueError('incomplete finite replay')
    for p, row in zip(finite, replays):
        if row['position'] != list(p) or row['outcome'] != data['nodes'][key(p)]['outcome']:
            raise ValueError('false finite leaf')
    dependencies = sorted({n['fact'] for n in data['nodes'].values() if n['rule'] == 'baseline'})
    return {'valid': True, 'C': len(encoded), 'certificate_sha256': sha(encoded),
            'outcome': data['nodes'][data['root']]['outcome'], 'baseline': sha(baseline),
            'dependencies': dependencies, 'finite_replays': replays}


def adapt_reply(certificate):
    from sylver.verify_finite_reply import validate_certificate
    dest = key(validate_certificate(certificate))
    parent = key((*certificate['parent'], certificate['opponent_move']))
    return {'schema': SCHEMA, 'root': parent, 'nodes': {
        parent: {'rule': 'edge', 'outcome': 'N', 'move': certificate['reply'], 'child': dest},
        dest: {'rule': 'finite', 'outcome': 'P'}}}


def adapt_graph(certificate, baseline, root=None):
    """Adapt PR #4 without modifying any archived bytes or trusting new leaves."""
    from .snapshot import fact_id
    nodes = {}
    for k, f in certificate['support'].items():
        p = from_key(k)
        ev = f['evidence']
        base = {'outcome': f['outcome']}
        if ev['kind'] == 'winning-edge':
            n = dict(base, rule='edge', move=ev['move'], child=ev['destination'])
        elif ev['kind'] == 'complete-cover':
            tail = 'quiet-end-v1' if ev['tail'] == 'quiet-end-theorem' else ev['tail']
            n = dict(base, rule='cover', tail=tail,
                     children=[{'move': r['move'], 'child': r['destination']} for r in ev['obligations']])
        elif gcd(*p) == 1:
            n = dict(base, rule='finite')
        else:
            ident = fact_id(p, f['outcome'])
            if ident not in baseline['facts']:
                raise ValueError(f'missing named historical dependency: {k}')
            n = dict(base, rule='baseline', fact=ident)
        nodes[k] = n
    return {'schema': SCHEMA, 'root': root or certificate['roots'][0], 'nodes': nodes}
