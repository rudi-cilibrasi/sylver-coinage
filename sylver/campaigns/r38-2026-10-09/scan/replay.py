"""Write finite-witness certificates and replay them (native, and Python unless REPLAY_PYTHON=0).

Usage: replay.py EVIDENCE PREFIX OUTDIR NAME. Each finite row of EVIDENCE (a
reply m to the evidence's position and an answer w) becomes
OUTDIR/<PREFIX><m>-certificate.json (schema 1, as in the U record), and
verify_finite_reply.py replays it into OUTDIR/verification/<PREFIX><m>/.
Jobs run in parallel, largest first, while their estimated memory (about 160
bytes per state, plus 0.25 GiB) stays within the budget.
"""
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path('/home/ruclaw/src/sylver-coinage')
sys.path.insert(0, str(ROOT))
from sylver.arena.common import position  # noqa: E402

HERE = Path(__file__).resolve().parent
BUDGET_GIB = float(__import__('os').environ.get('REPLAY_BUDGET_GIB', 30))
MAX_JOBS = int(__import__('os').environ.get('REPLAY_MAX_JOBS', 6))


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
        hours = max(1.0, row['states'] / 12_000 / 3600 * 1.5)
        jobs.append((row['states'], m, path, gib, cap, hours))
    jobs.sort(reverse=True)
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
    failed = {m: rc for m, rc in results.items() if rc != 0}
    print('finished:', len(results), 'failed:', failed, flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
