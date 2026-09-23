import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from sylver.arena.common import read, write

ROOT=Path(__file__).resolve().parents[2]


class AccountingTests(unittest.TestCase):
    def run_code(self,code,cpu=3,wall=5):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);config=p/'config.json'
            write(config,{'command':[sys.executable,'-c',code],'output':str(p/'run'),
                          'limits':{'cpu_seconds':cpu,'wall_seconds':wall,'memory_mb':256}})
            subprocess.run([sys.executable,'-m','sylver.arena.supervisor',str(config)],
                           cwd=ROOT,check=True,timeout=10)
            return read(p/'run/usage.json')

    def test_sleep_is_not_cpu(self):
        r=self.run_code('import time;time.sleep(.3)')
        self.assertGreater(r['wall_seconds'],.3)
        self.assertLess(r['cpu_seconds'],.2)
        self.assertEqual(r['returncode'],0)

    def test_cpu_and_parallel_workers_are_summed(self):
        code='import time\ns=time.process_time()\nwhile time.process_time()-s<.15:pass'
        r=self.run_code('import subprocess,sys\nps=[subprocess.Popen([sys.executable,"-c",'+repr(code)+']) for _ in range(3)]\nfor p in ps:p.wait()')
        self.assertGreater(r['cpu_seconds'],.45)
        self.assertIsNone(r['reason'])

    def test_orphaned_new_session_is_killed_and_charged(self):
        code='import time\ns=time.process_time()\nwhile time.process_time()-s<.15:pass\ntime.sleep(5)'
        r=self.run_code('import subprocess,sys,time\nsubprocess.Popen([sys.executable,"-c",'+repr(code)+'],start_new_session=True)\ntime.sleep(.25)')
        self.assertEqual(r['reason'],'orphaned-descendants')
        self.assertGreater(r['cpu_seconds'],.15)
        self.assertGreaterEqual(len(r['reaped']),2)
        self.assertTrue(any(x['returncode']<0 for x in r['reaped']))

    def test_cpu_kill_is_measured(self):
        r=self.run_code('while True:pass',cpu=.15)
        self.assertEqual(r['reason'],'cpu-limit')
        self.assertGreater(r['cpu_seconds'],.15)
        self.assertLess(r['wall_seconds'],3)

    def test_cancellation_preserves_cpu_and_reaps_worker(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);config=p/'config.json';ready=p/'ready'
            code=('import os,time\nfrom pathlib import Path\ns=time.process_time()\n'
                  'while time.process_time()-s<.1:pass\n'
                  'Path('+repr(str(ready))+').write_text(str(os.getpid()))\ntime.sleep(30)')
            write(config,{'command':[sys.executable,'-c',code],'output':str(p/'run'),
                          'limits':{'cpu_seconds':3,'wall_seconds':5,'memory_mb':256}})
            proc=subprocess.Popen([sys.executable,'-m','sylver.arena.supervisor',str(config)],cwd=ROOT)
            try:
                deadline=time.monotonic()+5
                while not ready.exists() and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue(ready.exists())
                worker=int(ready.read_text());proc.terminate();proc.wait(timeout=3)
                r=read(p/'run/usage.json')
                self.assertEqual(r['reason'],'cancelled')
                self.assertGreater(r['cpu_seconds'],.1)
                with self.assertRaises(ProcessLookupError):os.kill(worker,0)
            finally:
                if proc.poll() is None:proc.terminate();proc.wait(timeout=3)

    def test_address_space_limit_retains_failure_cost(self):
        r=self.run_code('x=bytearray(512*1024*1024)')
        self.assertNotEqual(r['returncode'],0)
        self.assertGreater(r['cpu_seconds'],0)
