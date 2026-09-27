import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from sylver.arena import sandbox
from sylver.arena.agent import command_response
from sylver.arena.common import ROOT

PROBE = '''import json, os, socket, sys
from pathlib import Path
p = Path(TARGET); result = {}
def attempt(name, action):
    try:
        action(); result[name] = True
    except OSError:
        result[name] = False
attempt("read", lambda: p.read_bytes())
attempt("write", lambda: p.write_text("tamper"))
attempt("list", lambda: os.listdir(p.parent))
attempt("tcp", lambda: socket.create_connection(("127.0.0.1", 9), timeout=1))
attempt("udp", lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
attempt("unix", lambda: socket.socket(socket.AF_UNIX, socket.SOCK_STREAM))
attempt("signal", lambda: os.kill(PARENT, 0))
attempt("scratch", lambda: Path("scratch.txt").write_text("ok"))
result["visible"] = p.exists()
print(json.dumps(result))
'''


class AgentIsolationTests(unittest.TestCase):
    def run_probe(self, backend=None):
        with tempfile.TemporaryDirectory() as d:
            source = ROOT/'sylver/arena/proof.py'; before = source.read_bytes()
            # Files named in argv are deliberately readable provider files, so
            # the probe target is embedded in the script instead.
            p = Path(d); script = p/'provider.py'
            script.write_text(f'TARGET = {str(source)!r}\nPARENT = {os.getpid()}\n' + PROBE)
            env = {'SYLVER_ARENA_SANDBOX': backend} if backend else {}
            with patch.dict(os.environ, env):
                sandbox._cache.clear()
                try:
                    result = command_response(['/usr/bin/python3', str(script)], {}, p/'run', 10)
                finally:
                    sandbox._cache.clear()
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(json.loads((p/'run/sandbox.json').read_text())['backend'], backend or sandbox.backend())
            return result

    def test_provider_cannot_read_or_rewrite_trusted_checkout(self):
        if sandbox.backend() == 'none':
            self.skipTest('no sandbox backend on this host')
        r = self.run_probe()
        self.assertFalse(r['read']); self.assertFalse(r['write']); self.assertFalse(r['list'])
        self.assertFalse(r['tcp']); self.assertFalse(r['udp']); self.assertFalse(r['unix'])
        self.assertTrue(r['scratch'])
        if sandbox.backend() == 'bwrap':
            self.assertFalse(r['visible'])  # Landlock hides contents, not existence.

    def test_landlock_backend_confines_provider(self):
        if sandbox.landlock_abi() < 1:
            self.skipTest('Landlock unsupported by this kernel')
        r = self.run_probe('landlock')
        for name in ('read', 'write', 'list', 'tcp', 'udp', 'unix'):
            self.assertFalse(r[name], name)
        if sandbox.landlock_abi() >= 6:
            self.assertFalse(r['signal'])   # scoped: cannot signal the test process
        self.assertTrue(r['scratch'])

    def test_unavailable_sandbox_fails_closed(self):
        with patch.object(sandbox, 'backend', return_value='none'):
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaisesRegex(ValueError, 'sandbox unavailable'):
                    command_response(['/usr/bin/python3', '-c', 'print(1)'], {}, Path(d)/'run', 3)

    def test_provider_credential_echo_is_not_preserved(self):
        if sandbox.backend() == 'none':
            self.skipTest('no sandbox backend on this host')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);script=p/'provider.py'
            script.write_text('import os,sys,time\n'
                              'print(os.environ["ARENA_TEST_TOKEN"],flush=True)\n'
                              'print(os.environ["ARENA_TEST_TOKEN"],file=sys.stderr,flush=True)\n'
                              'time.sleep(5)\n')
            with patch.dict(os.environ,{'ARENA_TEST_TOKEN':'private-test-credential'}):
                with self.assertRaises(ValueError):
                    command_response(['/usr/bin/python3',str(script)],{},p/'run',.2,credentials=['ARENA_TEST_TOKEN'])
            for f in (p/'run').iterdir():
                self.assertNotIn('private-test-credential',f.read_text())
