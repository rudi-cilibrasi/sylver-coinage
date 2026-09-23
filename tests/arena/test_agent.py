import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from sylver.arena.agent import command_response
from sylver.arena.common import ROOT


class AgentIsolationTests(unittest.TestCase):
    def test_provider_cannot_read_or_rewrite_trusted_checkout(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);script=p/'provider.py'
            source=ROOT/'sylver/arena/proof.py';before=source.read_bytes()
            script.write_text('import json\nfrom pathlib import Path\np=Path('+repr(str(source))+')\n'
                              'visible=p.exists()\ntry:\n p.write_text("tamper")\n changed=True\n'
                              'except OSError:changed=False\nprint(json.dumps(dict(visible=visible,changed=changed)))\n')
            result=command_response(['/usr/bin/python3',str(script)],{},p/'run',3)
            self.assertFalse(result['visible']);self.assertFalse(result['changed'])
            self.assertEqual(source.read_bytes(),before)

    def test_provider_credential_echo_is_not_preserved(self):
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
