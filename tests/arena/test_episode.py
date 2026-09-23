import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

from sylver.arena.common import read
from sylver.arena.episode import DEFAULT_LIMITS, resume_episode, run_episode, score
from sylver.arena.fixtures import build_fixtures, make_bundle, tiny_baseline
from sylver.arena.policies import BASELINES
from sylver.arena.protocol import Client, Session
from sylver.arena.exact import build_tools


class EpisodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.tools=Path(cls.tmp.name)/'tools'
        cls.binary=build_tools(cls.tools)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_score_formula(self):
        self.assertEqual(score(0,0)[0],100)
        self.assertEqual(score(100,1)[0],400)
        self.assertAlmostEqual(score(100,1)[1],math.log(400))
        for c,t in ((-1,0),(1,-1),(True,0),(1,float('nan'))):
            with self.assertRaises(ValueError):score(c,t)

    def test_all_policies_solve_edge_and_complete_short_cover(self):
        with tempfile.TemporaryDirectory() as d:
            for name,policy in BASELINES.items():
                for p in ([4,5],[4,6]):
                    with self.subTest(policy=name,p=p):
                        out=Path(d)/(name+'-'+str(p[1]))
                        receipt=run_episode(make_bundle(p,tiny_baseline(),'training'),policy,out,self.tools)
                        self.assertEqual(receipt['status'],'valid',receipt)
                        self.assertGreater(receipt['discovery_cpu'],0)
                        self.assertGreater(receipt['verification_cpu'],0)
                        self.assertAlmostEqual(receipt['T'],receipt['discovery_cpu']+receipt['verification_cpu'])
                        self.assertEqual(receipt['S'],score(receipt['C'],receipt['T'])[0])
                        with self.assertRaises(ValueError):resume_episode(out)
                        with self.assertRaises(FileExistsError):run_episode(make_bundle(p,tiny_baseline(),'training'),policy,out,self.tools)

    def test_resume_retains_all_costs_and_discoveries(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'run'
            script=[{'id':1,'op':'exact','args':{'positions':[[4,5,11]],'seconds':.2}}]
            first=run_episode(make_bundle([4,5],tiny_baseline(),'training'),None,path,self.tools,script=script)
            self.assertEqual(first['status'],'unsolved')
            second=resume_episode(path,self.tools)
            self.assertGreater(second['T'],first['T'])
            self.assertEqual(second['attempts'],2)
            self.assertIsNone(second['S'])
            self.assertEqual(len(second['phases']),2)
            self.assertTrue((path/'receipt-before-resume-0001.json').exists())
            self.assertIn('4,5,11',read(path/second['checkpoint']))

    def test_false_finite_submission_gets_no_score(self):
        with tempfile.TemporaryDirectory() as d:
            script=[{'id':1,'op':'submit','args':{'proof':{'schema':1,'root':'4,5','nodes':{
                '4,5':{'rule':'finite','outcome':'P'}}}}}]
            receipt=run_episode(make_bundle([4,5],tiny_baseline(),'training'),None,Path(d)/'run',self.tools,script=script)
            self.assertEqual(receipt['status'],'invalid')
            self.assertIsNone(receipt['S']);self.assertGreater(receipt['T'],0)

    def test_provider_overquota_and_unreported_usage_cannot_score(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);provider=root/'provider.py'
            limits=dict(DEFAULT_LIMITS,model_id='quota-test',model_requests=1,model_tokens=1)
            agent={'command':['/usr/bin/python3',str(provider)],'model_id':'quota-test',
                   'prompt':'default','limits':{'requests':1,'tokens':1,'cost':0.,'latency_seconds':2.}}
            action={'id':1,'op':'submit','args':{'proof':{'schema':1,'root':'4,5','nodes':{
                '4,5':{'rule':'finite','outcome':'N'}}}}}
            for name,body in [('overquota',json.dumps({'action':action,'usage':{
                    'input_tokens':2,'output_tokens':0,'cost':0.}})),
                    ('overcost',json.dumps({'action':action,'usage':{'input_tokens':0,'output_tokens':0,'cost':1.}})),
                    ('unreported','not json')]:
                provider.write_text('print('+repr(body)+')\n')
                r=run_episode(make_bundle([4,5],tiny_baseline(),'training',limits),None,root/name,self.tools,agent=agent)
                self.assertEqual(r['status'],'invalid',r)
                self.assertIsNone(r['S']);self.assertGreater(r['T'],0)
                self.assertEqual(r['model_usage']['requests'],1)
                if name=='overcost':self.assertEqual(r['model_usage']['cost'],1.)

    def test_timeout_and_unsupported_are_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            s=Session(make_bundle([4,5],tiny_baseline(),'training'),self.binary,d,DEFAULT_LIMITS)
            result=Client(s).call('exact',positions=[[16,26,62,85,98,134],[8,10,22]],seconds=1e-9)
            self.assertEqual([r['outcome'] for r in result['rows']],['unknown','unknown'])
            self.assertFalse(Client(s).call('profile',position=[8,10,22])['complete'])
            bad=Client(s).session.request({'id':3,'op':'submit','args':{'proof':{'path':'somewhere'}}})
            self.assertEqual(bad['result']['status'],'error')

    def test_heldout_visible_packages_do_not_contain_evaluator_data(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'fixtures';idx=build_fixtures(root)
            labels=read(root/'evaluator/labels.json')
            for name in idx['held-out']:
                bundle=read(root/'visible'/(name+'.json'))
                self.assertEqual(set(bundle),{'snapshot','manifest'})
                self.assertNotIn('label',json.dumps(bundle))
                self.assertNotIn('reference',json.dumps(bundle))
                self.assertNotIn('evaluator',json.dumps(bundle))
                self.assertNotIn('held-out-5-7',json.dumps(bundle))
            self.assertEqual(len(labels),8)
