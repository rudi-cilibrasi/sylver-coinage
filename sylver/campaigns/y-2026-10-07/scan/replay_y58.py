"""Write Y={16,28,58}'s finite-witness certificates and replay them (native + Python).

Each finite row of evidence_58.json becomes y<m>-certificate.json (schema 1, as in
the U record); verify_finite_reply.py --python replays it into verification/y<m>/.
Jobs run in parallel, largest first, while their estimated memory (Python is the
larger, about 160 bytes per state, plus 1 GiB) stays within the budget.
"""
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path('/home/ruclaw/src/sylver-coinage')
sys.path.insert(0, str(ROOT))
from sylver.arena.common import position  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / 'y58'
BUDGET_GIB, MAX_JOBS = 36, 6
Y = [16, 28, 58]


def main():
    evidence = json.loads((HERE / 'evidence_58.json').read_text())
    assert evidence['position'] == Y
    OUT.mkdir(exist_ok=True)
    jobs = []
    for row in evidence['rows']:
        if row['via'] != 'finite':
            continue
        m, w = row['obligation'], row['reply']
        dest = list(position((*Y, m, w)))
        cert = {'schema': 1, 'parent': Y, 'opponent_move': m, 'reply': w, 'destination': dest,
                'destination_outcome': 'P', 'frobenius': row['frobenius'],
                'consequence': f'Y+{m} is N by reply {w}.',
                'scope': 'Finite exhaustive-evaluation certificate. Replaying the destination requires no inherited '
                         'outcome cache, infinite-position certificate, or Quiet End Theorem.'}
        path = OUT / f'y{m}-certificate.json'
        path.write_text(json.dumps(cert, indent=2) + '\n')
        gib = max(2, int(row['states'] * 160 / 1024 ** 3) + 1)      # scheduling estimate
        cap = max(3, int(row['states'] * 220 / 1024 ** 3) + 2)      # per-solver address-space cap
        hours = max(1.0, row['states'] / 12_000 / 3600 * 1.5)
        jobs.append((row['states'], m, path, gib, cap, hours))
    jobs.sort(reverse=True)
    running, results = {}, {}
    while jobs or running:
        for m, (proc, gib, start) in list(running.items()):
            if proc.poll() is not None:
                results[m] = proc.returncode
                print(time.strftime('%H:%M:%S'), f'y{m} done rc={proc.returncode} {time.monotonic() - start:.0f}s', flush=True)
                del running[m]
        used = sum(gib for _, gib, _ in running.values())
        for job in list(jobs):   # first fit, largest first
            if len(running) >= MAX_JOBS:
                break
            states, m, path, gib, cap, hours = job
            if running and used + gib > BUDGET_GIB:
                continue
            jobs.remove(job)
            outdir = OUT / 'verification' / f'y{m}'
            if (outdir / 'receipt.json').exists() and json.loads((outdir / 'receipt.json').read_text()).get('status') == 'verified':
                results[m] = 0
                continue
            argv = [sys.executable, str(ROOT / 'sylver/verify_finite_reply.py'), '--certificate', str(path),
                    '--output', str(outdir), '--python', '--seconds', str(int(hours * 3600)), '--memory-gib', str(cap)]
            log = open(OUT / f'y{m}.log', 'w')
            running[m] = (subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT), gib, time.monotonic())
            used += gib
            print(time.strftime('%H:%M:%S'), f'start y{m} ({states:,} states, {gib} GiB cap)', flush=True)
        time.sleep(5)
    failed = {m: rc for m, rc in results.items() if rc != 0}
    print('finished:', len(results), 'failed:', failed, flush=True)


if __name__ == '__main__':
    main()
