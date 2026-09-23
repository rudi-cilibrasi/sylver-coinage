"""Bounded provider invocation for evolution, separate from deployment scoring."""
import sys
from pathlib import Path
from .agent import command_response
from .common import read, write

cfg=read(sys.argv[1]);out=Path(cfg['output']);out.mkdir()
write(out/'request.json',cfg['request'])
result=command_response(cfg['proposer']['command'],cfg['request'],out/'provider',cfg['seconds'],
                        cfg['proposer'].get('allow_network',False),cfg['proposer'].get('credentials',()))
write(out/'result.json',result)
