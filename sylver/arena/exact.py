"""Prebuilt exact evaluator and flush-preserving bounded finite batches."""
import os
from pathlib import Path
import re
import subprocess
import time
import tempfile

from .common import ROOT, key, legal, position, profile, sha, write

ROW=re.compile(r'position=([\d,]+) ([PN]) winning_move=(none|\d+) frobenius=(\d+) cumulative_states=(\d+)')


def build_tools(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    source=ROOT/'sylver/native_solver.cpp'
    binary=directory/f'native-{sha(source.read_bytes())[:16]}-16'
    if not binary.exists():
        # Atomic publication permits parallel episodes to share setup without
        # executing or overwriting a partially linked binary.
        with tempfile.TemporaryDirectory(dir=directory) as tmp:
            built=Path(tmp)/'native'
            subprocess.run(['g++','-std=c++20','-O3','-Wall','-Wextra','-pedantic',
                            '-DSYLVER_NATIVE_WORDS=16',str(source),'-o',str(built)],check=True)
            built.replace(binary)
    return binary.resolve()


def batch(binary, positions, directory, seconds):
    """Caller must be inside the accounted supervisor, including failed work."""
    directory=Path(directory);directory.mkdir()
    positions=[position(p) for p in positions]
    if any(profile(p).get('frobenius',1024)>1023 for p in positions):
        raise ValueError('unsupported exact query')
    request=directory/'positions.txt'
    request.write_text('\n'.join(map(key,positions))+'\n')
    command=[str(binary),'--batch-file',str(request)]
    start=time.monotonic()
    with (directory/'stdout.txt').open('w') as out,(directory/'stderr.txt').open('w') as err:
        process=subprocess.Popen(command,stdout=out,stderr=err)
        timeout=False
        try:process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timeout=True;process.kill();process.wait()
        finally:
            if process.poll() is None:process.kill();process.wait()
    rows=[];previous=0
    for line in (directory/'stdout.txt').read_text().splitlines():
        match=ROW.fullmatch(line)
        if not match:raise ValueError('truncated or malformed exact result')
        k,outcome,winner,f,states=match.groups()
        if len(rows)>=len(positions):raise ValueError('excess exact results')
        p=positions[len(rows)];move=None if winner=='none' else int(winner)
        if (k!=key(p) or int(f)!=profile(p)['frobenius'] or int(states)<previous
                or (outcome=='P')!=(move is None) or move is not None and not legal(p,move)):
            raise ValueError('invalid exact result')
        previous=int(states)
        rows.append({'position':list(p),'outcome':outcome,'winning_move':move,
                     'frobenius':int(f),'cumulative_states':int(states)})
    receipt={'returncode':process.returncode,'timeout':timeout,'completed':len(rows),
             'requested':len(positions),'wall_seconds':time.monotonic()-start,
             'rows':rows,'files':{n:sha((directory/n).read_bytes()) for n in
                                 ('positions.txt','stdout.txt','stderr.txt')}}
    write(directory/'receipt.json',receipt)
    if process.returncode==0 and len(rows)!=len(positions):raise ValueError('omitted exact results')
    return rows
