import copy
import json
from pathlib import Path
import tempfile
import unittest

from sylver.arena.common import canonical, key, profile, read, sha, write
from sylver.arena.snapshot import fact_id, manifest, snapshot, validate_bundle, validate_snapshot
from sylver.arena.proof import adapt_graph, adapt_reply, canonical_proof, verify, verifier_profile
from sylver.solver import solve_position

ROOT = Path(__file__).resolve().parents[2]


def python_batch(positions):
    return [dict(position=list(p), outcome='N' if solve_position(p).is_winning else 'P') for p in positions]


def finite(p, outcome):
    return {'schema': 1, 'root': key(p), 'nodes': {key(p): {'rule': 'finite', 'outcome': outcome}}}


class KnowledgeTests(unittest.TestCase):
    def test_canonicalization_matches_reference_semigroup_reduction(self):
        import itertools
        from sylver.arena.common import position
        from sylver.short_certificates import minimal_generators
        for p in itertools.combinations(range(2,24),3):
            self.assertEqual(position(p),minimal_generators(p))
        for p in ((16,26,62,95,98,102),(16,26,62,85,98,134),(8,12,26,30),(16,409,1023)):
            self.assertEqual(position(p),minimal_generators(p))

    def test_portable_deterministic_snapshot_and_conflict(self):
        a = {'position': [3, 2, 4], 'outcome': 'P', 'provenance': {'kind': 'test', 'artifacts': []}, 'dependencies': []}
        b = snapshot([a])
        self.assertEqual(b, snapshot([dict(a, position=[2, 3])]))
        with tempfile.TemporaryDirectory() as d:
            write(Path(d)/'snapshot.json', b)
            self.assertEqual(validate_snapshot(read(Path(d)/'snapshot.json')), sha(b))
        with self.assertRaises(ValueError):
            snapshot([a, dict(a, outcome='N')])
        with self.assertRaises(ValueError):
            snapshot([dict(a, dependencies=['missing'])])
        with self.assertRaises(ValueError):
            snapshot([dict(a, provenance={'kind':'test','artifacts':['0'*64]})])

    def test_visible_bundle_has_closed_fields_and_no_solved_target(self):
        b = snapshot()
        m = manifest([4, 5], b, verifier_profile(), {}, kind='held-out')
        bundle = {'manifest': m, 'snapshot': b}
        validate_bundle(bundle)
        for field in ('label', 'reference_proof', 'path', 'url', 'other_hidden_targets'):
            with self.assertRaises(ValueError):
                validate_bundle(dict(bundle, **{field: 'secret'}))
        solved = snapshot([{'position':[4,5], 'outcome':'N', 'provenance':{'kind':'test','artifacts':[]},'dependencies':[]}])
        with self.assertRaises(ValueError):
            manifest([4,5], solved, verifier_profile(), {})
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'duplicate.json'
            path.write_text('{"label":1,"label":2}')
            with self.assertRaises(ValueError):
                read(path)

    def test_finite_and_complete_cover(self):
        b = snapshot()
        p = finite([2,3], 'P')
        encoded = canonical_proof(p, b)
        report = verify(p, b, [2,3], python_batch)
        self.assertEqual(report['C'], len(encoded))
        self.assertTrue(report['valid'])
        cover = finite([2,3], 'P')
        cover['nodes']['2,3'] = {'rule':'cover','outcome':'P','tail':'finite','children':[]}
        verify(cover,b,[2,3],python_batch)
        with self.assertRaises(ValueError):
            verify(finite([4,5], 'P'), b, [4,5], python_batch)

    def test_edges_deduplication_and_rejections(self):
        b = snapshot()
        proof = {'schema':1, 'root':'4,5', 'nodes': {
            '4,5': {'rule':'edge','outcome':'N','move':11,'child':'4,5,11'},
            '4,5,11': {'rule':'finite','outcome':'P'}}}
        original = canonical_proof(proof,b)
        self.assertTrue(verify(proof,b,[4,5],python_batch)['valid'])
        proof['nodes'] = dict(reversed(list(proof['nodes'].items())))
        proof['nodes']['2,3'] = {'rule':'finite','outcome':'P'}
        self.assertEqual(canonical_proof(proof,b),original)
        for change in ({'move':8}, {'child':'4,5'}, {'rule':'url','url':'proof.json'}):
            wrong=copy.deepcopy(proof);wrong['nodes']['4,5'].update(change)
            with self.assertRaises(ValueError):
                canonical_proof(wrong,b)
        del proof['nodes']['4,5,11']
        with self.assertRaises(ValueError):
            canonical_proof(proof,b)

    def test_cover_order_and_baseline_cycles(self):
        p=(4,5,11);info=profile(p);nodes={};children=[]
        for move in info['moves']:
            child=key((*p,move));nodes[child]={'rule':'finite','outcome':'N'}
            children.append({'move':move,'child':child})
        nodes[key(p)]={'rule':'cover','outcome':'P','tail':'finite','children':children}
        proof={'schema':1,'root':key(p),'nodes':nodes}
        expected=canonical_proof(proof,snapshot())
        proof['nodes'][key(p)]['children'].reverse()
        self.assertEqual(canonical_proof(proof,snapshot()),expected)
        verify(proof,snapshot(),p,python_batch)
        a={'position':[2,3],'outcome':'P','provenance':{'kind':'test','artifacts':[]},'dependencies':[fact_id([4,5],'N')]}
        b={'position':[4,5],'outcome':'N','provenance':{'kind':'test','artifacts':[]},'dependencies':[fact_id([2,3],'P')]}
        with self.assertRaises(ValueError):snapshot([a,b])
        for reference in ('proof.json','https://example.invalid/proof'):
            with self.assertRaises(ValueError):
                canonical_proof({'schema':1,'root':'2,3','nodes':{'2,3':{'rule':'baseline','outcome':'P','fact':reference}}},snapshot())

    def test_unproved_tail_and_missing_cover_rejected(self):
        for p in ([8,10,22], [4,6]):
            info=profile(p)
            proof={'schema':1,'root':key(p),'nodes':{key(p):{
                'rule':'cover','outcome':'P','tail':info['tail'],'children':[]}}}
            with self.assertRaises(ValueError):
                canonical_proof(proof,snapshot())

    def test_historical_adapters_structural_validation(self):
        reply=read(ROOT/'sylver/campaigns/w-seven-2026-09-22/w134-certificate.json')
        canonical_proof(adapt_reply(reply),snapshot())
        cert=read(ROOT/'sylver/campaigns/targeted-2026-09-22/b-certificate.json')
        facts=[]
        for k,f in cert['support'].items():
            if f['evidence']['kind']=='repository-certificate':
                facts.append({'position':list(map(int,k.split(','))), 'outcome':f['outcome'],
                              'provenance':{'kind':'named-historical-certificate','artifacts':[]},'dependencies':[]})
        b=snapshot(facts)
        for root in cert['roots']:
            data=canonical_proof(adapt_graph(cert,b,root),b)
            self.assertGreater(len(json.loads(data)['nodes']),100)
