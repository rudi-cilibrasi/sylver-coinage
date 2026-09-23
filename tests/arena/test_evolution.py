import copy
import json
from pathlib import Path
import tempfile
import unittest
from sylver.arena.common import ROOT, read, sha
from sylver.arena.episode import DEFAULT_LIMITS, run_episode
from sylver.arena.evolution import fitness, run_evolution, selection
from sylver.arena.fixtures import make_bundle, tiny_baseline
from sylver.arena.policies import BASELINES


def mock_agent():
    return {'command':['/usr/bin/python3',str(ROOT/'sylver/arena/mock_provider.py')],
            'model_id':'offline-mock-v1','prompt':'default','limits':{'requests':12,'tokens':20000,'cost':0.,'latency_seconds':3.}}


class EvolutionTests(unittest.TestCase):
    def test_infinite_fitness_and_deterministic_selection(self):
        self.assertIsNone(fitness([{'status':'invalid','log_score':-1000}]))
        self.assertEqual(fitness([{'status':'valid','log_score':2},{'status':'valid','log_score':4}]),3)
        candidate={'policy':BASELINES['increasing'],'prompt':'default','mode':'policy'}
        rows=[{'id':'b','candidate':candidate,'fitness':4},{'id':'a','candidate':candidate,'fitness':4},
              {'id':'x','candidate':candidate,'fitness':None}]
        self.assertEqual(selection(rows)['best'],'a')
        self.assertEqual(selection(rows),selection(list(reversed(rows))))

    def test_mock_agent_same_api_and_evolution_rejection_lineage(self):
        limits=dict(DEFAULT_LIMITS,model_requests=12,model_tokens=20000,model_id='offline-mock-v1')
        bundle=make_bundle([4,6],tiny_baseline(),'training',limits)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            r=run_episode(bundle,None,root/'agent',root/'tools',agent=mock_agent())
            self.assertEqual(r['status'],'valid',r)
            self.assertGreater(r['model_usage']['requests'],0)
            result=run_evolution([bundle],root/'evolve',root/'tools',max_candidates=7,
                                 agent_template=mock_agent())
            self.assertTrue(result['best'])
            self.assertTrue(any(r['status']=='invalid' and r['parent'] for r in result['records']))
            self.assertTrue(any(r['candidate']['mode']=='prompt' and r['fitness'] is not None for r in result['records']))
            self.assertEqual(selection(read(root/'evolve/records.json'))['best'],result['best'])
            for row in result['records']:
                if row['status']=='invalid':self.assertIsNone(row['fitness'])

    def test_configurable_mock_proposer_and_generation_accounting(self):
        limits=dict(DEFAULT_LIMITS,model_requests=12,model_tokens=20000,model_id='offline-mock-v1')
        bundle=make_bundle([4,6],tiny_baseline(),'training',limits)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            result=run_evolution([bundle],root/'e',root/'tools',max_candidates=6,
                                 proposer={'command':mock_agent()['command']},
                                 model_requests=1,model_tokens=20000,agent_template=mock_agent())
            self.assertEqual(len(result['records']),6)
            self.assertEqual(result['generation_model_usage']['requests'],1)
            self.assertGreater(result['generation_cpu'],0)
            self.assertTrue((root/'e/generation-005/accounting/usage.json').exists())
            self.assertEqual(read(root/'e/generation-005/work/request.json')['remaining_model_budget'],
                             {'requests':1,'tokens':20000,'cost':0.})
            self.assertEqual(result['records'][-1]['status'],'valid')

    def test_heldout_cannot_enter_selection(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                run_evolution([make_bundle([5,7],tiny_baseline(),'held-out')],Path(d)/'e',Path(d)/'tools')
