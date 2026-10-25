"""Write finite-witness certificates and replay them (native, and Python unless REPLAY_PYTHON=0).

Usage: replay.py EVIDENCE PREFIX OUTDIR NAME. Each finite row of EVIDENCE (a
reply m to the evidence's position and an answer w) becomes
OUTDIR/<PREFIX><m>-certificate.json (schema 1, as in the U record), and
verify_finite_reply.py replays it into OUTDIR/verification/<PREFIX><m>/.
Jobs run in parallel, largest first, while their estimated memory (about 160
bytes per state, plus 0.25 GiB) stays within the budget. A destination above
PYTHON_MAX states is too large for the Python evaluator here: after the others,
one at a time, it gets verify_finite_reply.py without --python, then a
sequential kunz_solver.cpp replay (--threads 1 --verify-memo) built from the
source snapshot the reply-38 audit pins, as the {16,38,72} certification
record (c72-2026-10-18) did for its largest witnesses (its replay.py). Exits
1 if a job fails.
"""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path('/home/ruclaw/src/sylver-coinage')
sys.path.insert(0, str(ROOT))
from sylver.arena.common import position  # noqa: E402

HERE = Path(__file__).resolve().parent
BUDGET_GIB = float(__import__('os').environ.get('REPLAY_BUDGET_GIB', 30))
MAX_JOBS = int(__import__('os').environ.get('REPLAY_MAX_JOBS', 6))
PYTHON_MAX = 150_000_000
SNAPSHOT = ROOT / 'sylver/campaigns/r38-2026-10-09/verification/sources/kunz_solver-243866d.cpp'
SNAPSHOT_SHA256 = '4b6221788c1e76805bbf7d680a493e7c21c9664a2ef3274ff50487302cd2c672'
KUNZ_OPTIONS = ['--threads', '1', '--verify-memo', '--verify-threads', '6', '--memo-stats']
BUILD = ['g++', '-std=c++20', '-O3', '-Wall', '-Wextra', '-pedantic', '-Werror', '-pthread', '-march=native']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kunz_replay(out, cert):
    """The second replay of a large destination, into ``out``: sequential kunz_solver with --verify-memo,
    timed (the {16,38,72} certification record's replay.py, with the binary built into verification/sources/build/).
    A receipt already there is kept only if it records a P result."""
    if (out / 'kunz-receipt.json').exists():
        old = json.loads((out / 'kunz-receipt.json').read_text())
        if old.get('returncode') == 0 and old.get('outcome') == 'P':
            return
    if digest(SNAPSHOT) != SNAPSHOT_SHA256:
        raise SystemExit('the pinned kunz_solver.cpp snapshot has changed')
    binary = out.parent / 'sources/build/kunz-243866d'   # build/ is ignored by git
    binary.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([*BUILD, str(SNAPSHOT), '-o', str(binary)], check=True)   # each time, from the snapshot
    dest = cert['destination']
    command = ['kunz-243866d', *KUNZ_OPTIONS, *map(str, dest)]
    stdout, stderr = out / 'kunz-stdout.txt', out / 'kunz-stderr.txt'
    start = time.monotonic()
    with stdout.open('w') as o, stderr.open('w') as e:
        rc = subprocess.run(['/usr/bin/time', '-v', str(binary), *command[1:]], stdout=o, stderr=e).returncode
    lines = stdout.read_text().splitlines()
    states = int(lines[0].split('states=')[1]) if rc == 0 and lines and 'states=' in lines[0] else None
    rss = next((int(l.split(':')[1]) for l in stderr.read_text().splitlines() if 'Maximum resident' in l), None)
    receipt = {'position': dest, 'frobenius': cert['frobenius'], 'source': 'sylver/kunz_solver.cpp',
               'commit': '243866dee3241de02b75a96c42072f9ec6e47dd3',
               'source_snapshot': os.path.relpath(SNAPSHOT, out), 'source_sha256': SNAPSHOT_SHA256,
               'build': ' '.join(BUILD), 'binary_sha256': digest(binary),
               'command': command, 'returncode': rc, 'elapsed_seconds': round(time.monotonic() - start, 1),
               'max_rss_kib': rss, 'stdout_sha256': digest(stdout), 'stderr_sha256': digest(stderr),
               'outcome': 'P' if lines[:1] and lines[0].startswith('P ') else None, 'states': states}
    (out / 'kunz-receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')


def main(evidence_file, prefix, outdir, name):
    evidence = json.loads((HERE / evidence_file).read_text())
    Y = evidence['position']
    OUT = HERE / outdir
    (OUT / 'verification').mkdir(parents=True, exist_ok=True)
    jobs = []
    for row in evidence['rows']:
        if row['via'] != 'finite':
            continue
        m, w = row['obligation'], row['reply']
        dest = list(position((*Y, m, w)))
        cert = {'schema': 1, 'parent': Y, 'opponent_move': m, 'reply': w, 'destination': dest,
                'destination_outcome': 'P', 'frobenius': row['frobenius'],
                'consequence': f'{name}+{m} is N by reply {w}.',
                'scope': 'Finite exhaustive-evaluation certificate. Replaying the destination requires no inherited '
                         'outcome cache, infinite-position certificate, or Quiet End Theorem.'}
        path = OUT / f'{prefix}{m}-certificate.json'
        path.write_text(json.dumps(cert, indent=2) + '\n')
        gib = row['states'] * float(__import__('os').environ.get('REPLAY_BYTES_PER_STATE', 160)) / 1024 ** 3 + 0.25
        cap = max(3, int(row['states'] * 220 / 1024 ** 3) + 2)      # per-solver address-space cap
        hours = max(1.0, row["states"] / float(__import__("os").environ.get("REPLAY_RATE", 12_000)) / 3600 * 1.5)
        jobs.append((row['states'], m, path, gib, cap, hours))
    jobs.sort(reverse=True)
    large = [job for job in jobs if job[0] > PYTHON_MAX]
    jobs = [job for job in jobs if job[0] <= PYTHON_MAX]
    running, results = {}, {}
    while jobs or running:
        for m, (proc, gib, start) in list(running.items()):
            if proc.poll() is not None:
                results[m] = proc.returncode
                print(time.strftime('%H:%M:%S'), f'{prefix}{m} done rc={proc.returncode} {time.monotonic() - start:.0f}s', flush=True)
                del running[m]
        used = sum(gib for _, gib, _ in running.values())
        for job in list(jobs):   # first fit, largest first
            if len(running) >= MAX_JOBS:
                break
            states, m, path, gib, cap, hours = job
            if running and used + gib > BUDGET_GIB:
                continue
            jobs.remove(job)
            outdir = OUT / 'verification' / f'{prefix}{m}'
            if (outdir / 'receipt.json').exists() and json.loads((outdir / 'receipt.json').read_text()).get('status') == 'verified':
                results[m] = 0
                continue
            argv = [sys.executable, str(ROOT / 'sylver/verify_finite_reply.py'), '--certificate', str(path),
                    '--output', str(outdir), *(['--python'] if __import__('os').environ.get('REPLAY_PYTHON', '1') == '1' else []),
                    '--seconds', str(int(hours * 3600)), '--memory-gib', str(cap)]
            log = open(OUT / f'{prefix}{m}.log', 'w')
            running[m] = (subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT), gib, time.monotonic())
            used += gib
            print(time.strftime('%H:%M:%S'), f'start {prefix}{m} ({states:,} states, {gib} GiB cap)', flush=True)
        time.sleep(5)
    for states, m, path, gib, cap, hours in large:   # then the large ones, one at a time
        outdir = OUT / 'verification' / f'{prefix}{m}'
        start = time.monotonic()
        print(time.strftime('%H:%M:%S'), f'start {prefix}{m} ({states:,} states, native then kunz)', flush=True)
        receipt = outdir / 'receipt.json'
        if not (receipt.exists() and json.loads(receipt.read_text()).get('status') == 'verified'):
            with open(OUT / f'{prefix}{m}.log', 'w') as log:
                rc = subprocess.run([sys.executable, str(ROOT / 'sylver/verify_finite_reply.py'), '--certificate',
                                     str(path), '--output', str(outdir), '--seconds', str(int(hours * 3600)),
                                     '--memory-gib', str(cap)], stdout=log, stderr=subprocess.STDOUT).returncode
            if rc != 0:
                results[m] = rc
                print(time.strftime('%H:%M:%S'), f'{prefix}{m} native rc={rc}', flush=True)
                continue
        kunz_replay(outdir, json.loads(path.read_text()))
        kunz = json.loads((outdir / 'kunz-receipt.json').read_text())
        results[m] = 0 if kunz['returncode'] == 0 and kunz['outcome'] == 'P' else 1
        print(time.strftime('%H:%M:%S'), f'{prefix}{m} done rc={results[m]} {time.monotonic() - start:.0f}s', flush=True)
    failed = {m: rc for m, rc in results.items() if rc != 0}
    print('finished:', len(results), 'failed:', failed, flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]))
