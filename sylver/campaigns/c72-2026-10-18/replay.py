#!/usr/bin/env python3
"""Replay every c72 certificate from empty memos, several at a time within a memory budget.

Each destination of at most PYTHON_MAX states gets sylver.verify_finite_reply --python (native_solver.cpp
and the Python reference evaluator, equal state counts). The larger ones get verify_finite_reply
without --python, then a sequential kunz_solver.cpp replay (--threads 1 --verify-memo) built from the
source snapshot the reply-38 audit pins, as B56's largest witnesses did. sizes.json holds kunz's state
count for each destination, used only to order the replays and size their memory limits.
Usage: python replay.py [--jobs N] [--budget-gib G]. Writes verification/c72_<m>/; skips finished ones.
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R38 = ROOT / 'sylver/campaigns/r38-2026-10-09'
SNAPSHOT = R38 / 'verification/sources/kunz_solver-243866d.cpp'
SNAPSHOT_SHA256 = '4b6221788c1e76805bbf7d680a493e7c21c9664a2ef3274ff50487302cd2c672'
KUNZ_OPTIONS = ['--threads', '1', '--verify-memo', '--verify-threads', '6', '--memo-stats']
BUILD = ['g++', '-std=c++20', '-O3', '-Wall', '-Wextra', '-pedantic', '-Werror', '-pthread', '-march=native']
PYTHON_MAX = 150_000_000
GIB_PER_MILLION = 0.25          # the Python evaluator's peak, with room; native needs less


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kunz_binary():
    if digest(SNAPSHOT) != SNAPSHOT_SHA256:
        raise SystemExit('the pinned kunz_solver.cpp snapshot has changed')
    binary = HERE / 'verification/sources/kunz-243866d'
    binary.parent.mkdir(parents=True, exist_ok=True)
    if not binary.exists():
        subprocess.run([*BUILD, str(SNAPSHOT), '-o', str(binary)], check=True)
    return binary


def kunz_replay(name, cert):
    """The second replay of a large destination: sequential kunz_solver with --verify-memo, timed."""
    out = HERE / 'verification' / name
    if (out / 'kunz-receipt.json').exists():
        return
    binary = kunz_binary()
    dest = cert['destination']
    command = [f'kunz-243866d', *KUNZ_OPTIONS, *map(str, dest)]
    stdout, stderr = out / 'kunz-stdout.txt', out / 'kunz-stderr.txt'
    start = time.monotonic()
    with stdout.open('w') as o, stderr.open('w') as e:
        rc = subprocess.run(['/usr/bin/time', '-v', str(binary), *command[1:]], stdout=o, stderr=e).returncode
    lines = stdout.read_text().splitlines()
    states = int(lines[0].split('states=')[1]) if rc == 0 and lines and 'states=' in lines[0] else None
    rss = next((int(l.split(':')[1]) for l in stderr.read_text().splitlines() if 'Maximum resident' in l), None)
    receipt = {'position': dest, 'frobenius': cert['frobenius'], 'source': 'sylver/kunz_solver.cpp',
               'commit': '243866dee3241de02b75a96c42072f9ec6e47dd3',
               'source_snapshot': str(Path('../../..') / SNAPSHOT.relative_to(HERE.parent)),
               'source_sha256': SNAPSHOT_SHA256, 'build': ' '.join(BUILD), 'binary_sha256': digest(binary),
               'command': command, 'returncode': rc, 'elapsed_seconds': round(time.monotonic() - start, 1),
               'max_rss_kib': rss, 'stdout_sha256': digest(stdout), 'stderr_sha256': digest(stderr),
               'outcome': 'P' if lines[:1] and lines[0].startswith('P ') else None, 'states': states}
    (out / 'kunz-receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, default=6)
    parser.add_argument('--budget-gib', type=int, default=40)
    args = parser.parse_args()
    sizes = json.loads((HERE / 'sizes.json').read_text())
    todo = []
    for path in sorted(HERE.glob('c72_*-certificate.json')):
        name = path.name.removesuffix('-certificate.json')
        cert = json.loads(path.read_text())
        states = sizes[','.join(map(str, cert['destination']))]
        big = states > PYTHON_MAX
        gib = 80 if big else max(4, math.ceil(states / 1e6 * GIB_PER_MILLION) + 2)
        done = (HERE / 'verification' / name / 'receipt.json').exists()
        todo.append((big, -states, name, path, cert, gib, done))
    todo.sort()                                   # small ones first, largest of them first
    pending = [t for t in todo if not t[0] and not t[6]]
    running = []
    while pending or running:                     # start the largest pending replay that fits
        running = [(p, g) for p, g in running if p.poll() is None]
        free = args.budget_gib - sum(g for _, g in running)
        fits = [t for t in pending if t[5] <= free] if len(running) < args.jobs else []
        if not fits:
            time.sleep(5)
            continue
        _, _, name, path, cert, gib, _ = t = fits[0]
        pending.remove(t)
        log = (HERE / 'verification' / f'{name}.log').open('w')
        p = subprocess.Popen([sys.executable, '-m', 'sylver.verify_finite_reply', '--certificate', str(path),
                              '--output', str(HERE / 'verification' / name), '--python', '--seconds', '86400',
                              '--memory-gib', str(gib)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        running.append((p, gib))
        print('START', name, gib, 'GiB', flush=True)
    for big, _, name, path, cert, gib, done in todo:  # then the large ones, one at a time
        if not big or (done and (HERE / 'verification' / name / 'kunz-receipt.json').exists()):
            continue
        if not done:
            subprocess.run([sys.executable, '-m', 'sylver.verify_finite_reply', '--certificate', str(path),
                            '--output', str(HERE / 'verification' / name), '--seconds', '86400',
                            '--memory-gib', str(gib)], cwd=ROOT, check=True)
        kunz_replay(name, cert)
        print('DONE', name, flush=True)
    print('ALL DONE', flush=True)


if __name__ == '__main__':
    main()
