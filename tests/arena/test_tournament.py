import copy
from pathlib import Path
import shutil
import tempfile
import unittest

from sylver.arena.common import read, sha, write
from sylver.arena.episode import run_episode
from sylver.arena.fixtures import make_bundle, tiny_baseline
from sylver.arena.policies import BASELINES
from sylver.arena.snapshot import load_bundle, save_bundle
from sylver.arena.tournament import admit, leaderboard, render, reverify


class TournamentTests(unittest.TestCase):
    def test_portable_bundle_and_independent_reverification(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle=make_bundle([4,5],tiny_baseline(),'training')
            a=root/'a';a.mkdir();save_bundle(a/'challenge.json',bundle,compact=True)
            shutil.copytree(a,root/'b');shutil.rmtree(a)
            self.assertEqual(load_bundle(root/'b/challenge.json'),bundle)
            r=run_episode(bundle,BASELINES['increasing'],root/'episode',root/'tools')
            shutil.copytree(root/'episode',root/'relocated');shutil.rmtree(root/'episode')
            checked=reverify(root/'relocated',root/'replay',root/'tools')
            self.assertEqual(checked['C'],r['C'])
            self.assertTrue(checked['valid'])
            with self.assertRaises(ValueError):admit(root/'relocated',root/'admit',root/'tools')

    def test_profile_groups_and_outcomes_are_visible(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle=make_bundle([4,5],tiny_baseline(),'training')
            r=run_episode(bundle,BASELINES['interleaved'],root/'episode',root/'tools')
            different=copy.deepcopy(r);different['execution']['python']='different'
            self.assertEqual(len(leaderboard([('one',r),('two',different)])),2)
            text=render([('one',r)])
            self.assertIn('Target {4,5}',text);self.assertIn('Outcome',text)
            self.assertIn(' | N | ',text)

    def test_live_admission_creates_new_snapshot_only_after_replay(self):
        # Synthetic live challenge exercises the admission gate; this is not a
        # claim of mathematical novelty for the tiny public test position.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle=make_bundle([4,5],tiny_baseline(),'live')
            before=sha(bundle['snapshot'])
            run_episode(bundle,BASELINES['interleaved'],root/'episode',root/'tools')
            new=admit(root/'episode',root/'admitted',root/'tools')
            self.assertNotEqual(new,before)
            self.assertEqual(sha(read(root/'episode/bundle.json')['snapshot']),before)
            self.assertTrue(read(root/'admitted/python/verification.json')['valid'])
            self.assertTrue(any(f['position']==[4,5] for f in read(root/'admitted/snapshot.json')['facts'].values()))

    def test_reverify_from_another_source_checkout(self):
        import subprocess,sys
        from sylver.arena.common import ROOT
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle=make_bundle([4,5],tiny_baseline(),'training')
            run_episode(bundle,BASELINES['interleaved'],root/'episode',root/'tools')
            checkout=root/'checkout';package=checkout/'sylver';package.mkdir(parents=True)
            for name in ('__init__.py','solver.py','short_certificates.py','native_solver.cpp','verify_finite_reply.py'):
                shutil.copy2(ROOT/'sylver'/name,package/name)
            shutil.copytree(ROOT/'sylver/arena',package/'arena',ignore=shutil.ignore_patterns('__pycache__','data'))
            result=subprocess.run([sys.executable,'-m','sylver.arena','verify',str(root/'episode'),
                                   '--output',str(root/'replay'),'--tools',str(root/'other-tools')],
                                  cwd=checkout,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(read(root/'replay/reverification.json')['valid'])

    def test_interactive_protocol_queries_are_accounted(self):
        import subprocess,sys,json
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle=make_bundle([4,5],tiny_baseline(),'training')
            write(root/'bundle.json',bundle)
            request={'id':1,'op':'exact','args':{'positions':[[4,5,11]],'seconds':.2}}
            result=subprocess.run([sys.executable,'-m','sylver.arena','serve',str(root/'bundle.json'),
                                   '--output',str(root/'server')],input=json.dumps(request)+'\n',
                                  text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['result']['rows'][0]['outcome'],'P')
            self.assertGreater(read(root/'server/accounting/usage.json')['cpu_seconds'],0)
