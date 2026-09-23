"""Portable, content-addressed knowledge and label-free visible challenges."""
from pathlib import Path

from .common import SCHEMA, THEOREMS, canonical, fields, key, position, read, sha, write


def fact_id(p, outcome):
    return sha({'position': list(position(p)), 'outcome': outcome})


def snapshot(facts=(), artifacts=None, theorems=THEOREMS):
    records = {}
    for fact in facts:
        fields(fact, ('position', 'outcome', 'provenance', 'dependencies'))
        p = position(fact['position'])
        if fact['outcome'] not in ('P', 'N'):
            raise ValueError('unknown is not a baseline fact')
        record = dict(fact, position=list(p), dependencies=sorted(set(fact['dependencies'])))
        k = key(p)
        if k in records and records[k] != record:
            raise ValueError(f'conflicting outcome or provenance: {k}')
        records[k] = record
    data = {'schema': SCHEMA, 'facts': {fact_id(f['position'], f['outcome']): f
                                       for f in records.values()},
            'artifacts': artifacts or {}, 'theorems': sorted(theorems)}
    validate_snapshot(data)
    return data


def validate_snapshot(data):
    fields(data, ('schema', 'facts', 'artifacts', 'theorems'))
    if type(data['schema']) is not int or data['schema'] != SCHEMA:
        raise ValueError('unsupported snapshot schema')
    if not isinstance(data['facts'], dict) or not isinstance(data['artifacts'], dict):
        raise ValueError('expected fact and artifact maps')
    if (not isinstance(data['theorems'], list) or len(set(data['theorems'])) != len(data['theorems'])
            or set(data['theorems']) - set(THEOREMS)):
        raise ValueError('unsupported theorem library')
    for h, meta in data['artifacts'].items():
        if len(h) != 64 or any(c not in '0123456789abcdef' for c in h):
            raise ValueError('invalid artifact digest')
        fields(meta, ('kind',))
        if not isinstance(meta['kind'], str):
            raise ValueError('invalid artifact kind')
    positions = set()
    for ident, f in data['facts'].items():
        fields(f, ('position', 'outcome', 'provenance', 'dependencies'))
        if list(position(f['position'])) != f['position'] or f['outcome'] not in ('P', 'N'):
            raise ValueError('invalid canonical fact')
        if ident != fact_id(f['position'], f['outcome']) or key(f['position']) in positions:
            raise ValueError('conflicting or incorrectly addressed fact')
        positions.add(key(f['position']))
        fields(f['provenance'], ('kind', 'artifacts'))
        if not isinstance(f['provenance']['kind'], str):
            raise ValueError('invalid provenance')
        if any(a not in data['artifacts'] for a in f['provenance']['artifacts']):
            raise ValueError('missing provenance artifact')
        if any(d not in data['facts'] for d in f['dependencies']):
            raise ValueError('missing mathematical dependency')
    visited, active = set(), set()
    def visit(ident):
        if ident in active:
            raise ValueError('cyclic baseline dependencies')
        if ident in visited:
            return
        active.add(ident)
        for dep in data['facts'][ident]['dependencies']:
            visit(dep)
        active.remove(ident)
        visited.add(ident)
    for ident in data['facts']:
        visit(ident)
    return sha(data)


def manifest(target, baseline, verifier, execution, kind='training', context=''):
    validate_snapshot(baseline)
    p = list(position(target))
    if any(f['position'] == p for f in baseline['facts'].values()):
        raise ValueError('target already labeled in visible snapshot')
    if kind not in ('training', 'held-out', 'live', 'public-regression'):
        raise ValueError('invalid challenge kind')
    return {'schema': SCHEMA, 'target': p, 'baseline': sha(baseline),
            'verifier': verifier, 'execution': execution, 'kind': kind, 'context': context}


def validate_bundle(bundle):
    fields(bundle, ('manifest', 'snapshot'))
    m = bundle['manifest']
    fields(m, ('schema', 'target', 'baseline', 'verifier', 'execution', 'kind', 'context'))
    expected = manifest(m['target'], bundle['snapshot'], m['verifier'], m['execution'], m['kind'], m['context'])
    if m != expected or type(m['schema']) is not int:
        raise ValueError('challenge manifest mismatch')
    # All visible fields are closed schemas. No arbitrary paths, URLs, labels,
    # proof payloads, or evaluator metadata can be smuggled into the package.
    if not isinstance(m['context'], str) or not isinstance(m['execution'], dict):
        raise ValueError('invalid challenge context/profile')
    return sha(m)


def export_graph(graph_path, repo, include_cache=True):
    """Import frozen campaign facts without following historical absolute paths.

    The entire starting corpus is an explicit assumption of a competition;
    importing is not a new proof of the historical database.
    """
    repo, graph_path = Path(repo), Path(graph_path)
    graph = read(graph_path)
    artifacts = {sha(graph_path.read_bytes()): {'kind': 'campaign-graph'}}
    source_hash = next(iter(artifacts))
    facts = {}
    for historical, meta in graph['sources'].items():
        suffix = historical.split('/sylver/', 1)
        if len(suffix) != 2:
            raise ValueError('unrecognized historical cache path')
        cache = (repo / 'sylver' / suffix[1]).resolve()
        if not cache.is_relative_to(repo.resolve()):
            raise ValueError('cache path escapes repository')
        if sha(cache.read_bytes()) != meta['sha256']:
            raise ValueError('cache fingerprint mismatch')
        artifacts[meta['sha256']] = {'kind': 'exact-cache'}
        if include_cache:
            for line in cache.read_text().splitlines():
                k, result = line.split()
                if result not in ('0', '1'):
                    raise ValueError('invalid cache outcome')
                p = position([int(x) for x in k.split(',')])
                k = key(p)
                outcome = 'P' if result == '1' else 'N'
                f = {'position': list(p), 'outcome': outcome,
                     'provenance': {'kind': 'exact-cache', 'artifacts': [meta['sha256']]},
                     'dependencies': []}
                if k in facts and facts[k]['outcome'] != outcome:
                    raise ValueError('cache conflict')
                facts[k] = f
    support = graph['support']
    for k, f in support.items():
        p = position([int(x) for x in k.split(',')])
        k = key(p)
        if k in facts and facts[k]['outcome'] != f['outcome']:
            raise ValueError('graph/cache conflict')
        ev = f['evidence']
        deps = ([ev['destination']] if ev['kind'] == 'winning-edge' else
                [r['destination'] for r in ev['obligations']] if ev['kind'] == 'complete-cover' else [])
        facts[k] = {'position': list(p), 'outcome': f['outcome'],
                    'provenance': {'kind': ev['kind'], 'artifacts': [source_hash]},
                    'dependencies': deps}
    for f in facts.values():
        f['dependencies'] = [fact_id(facts[d]['position'], facts[d]['outcome']) for d in f['dependencies']]
    return snapshot(facts.values(), artifacts)


def save_bundle(path,bundle,compact=False):
    """Optional deduplicated, content-addressed baseline beside manifests."""
    import gzip
    path=Path(path);validate_bundle(bundle)
    if not compact:
        write(path,bundle);return
    directory=path.parent/'knowledge';directory.mkdir(exist_ok=True)
    h=sha(bundle['snapshot']);stored=directory/(h+'.json.gz')
    encoded=canonical(bundle['snapshot'])
    if not stored.exists():stored.write_bytes(gzip.compress(encoded,mtime=0))
    write(path,{'manifest':bundle['manifest'],'snapshot_sha256':h})


def load_bundle(path):
    import gzip
    from .common import decode
    path=Path(path);value=read(path)
    if 'snapshot_sha256' in value:
        fields(value,('manifest','snapshot_sha256'))
        h=value['snapshot_sha256']
        if not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):
            raise ValueError('invalid baseline address')
        if value['manifest']['baseline']!=h:raise ValueError('baseline reference mismatch')
        stored=path.parent/'knowledge'/(h+'.json.gz')
        encoded=gzip.decompress(stored.read_bytes())
        if sha(encoded)!=h:raise ValueError('baseline content mismatch')
        value={'manifest':value['manifest'],'snapshot':decode(encoded)}
    validate_bundle(value)
    return value
