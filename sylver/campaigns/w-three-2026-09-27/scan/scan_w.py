#!/usr/bin/env python3
"""Parallel finite witness scan for W={16,26,62,98}'s five open moves.

Each query is an independent fresh-memo native evaluation of W+m+r for odd
r.  A P result means r answers move m (new result; needs independent replay).
Killed/over-budget queries are recorded as unknown, never as outcomes.
Restartable: rows already in the ledger are skipped.
"""
import argparse, json, os, resource, signal, subprocess, sys, time
from pathlib import Path

REPO = Path('/home/ruclaw/src/sylver-coinage')
sys.path.insert(0, str(REPO))
from sylver.short_certificates import minimal_generators
from sylver.solver import frobenius_number

W = (16, 26, 62, 98)
MOVES = (70, 86, 92, 108, 118)


WINNERS = {}  # position -> known winning move (graph evidence)


def known_outcomes():
    known = {}
    g = json.load(open(REPO / 'sylver/campaigns/w-six-2026-09-22/evidence/proof-graph.json'))
    for k, f in g['support'].items():
        known[tuple(map(int, k.split(',')))] = f['outcome']
        ev = f['evidence']
        mv = ev.get('move') or ev.get('winning_move')
        if f['outcome'] == 'N' and mv:
            WINNERS[tuple(map(int, k.split(',')))] = mv
    for line in open(REPO / 'sylver/move26_data/periodicity_x.cache'):
        k, v = line.split()
        known.setdefault(tuple(map(int, k.split(','))), 'P' if v == '1' else 'N')
    return known


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--binary', type=Path, required=True)
    ap.add_argument('--narrow-binary', type=Path, help='4-word build used when Frobenius <= 255')
    ap.add_argument('--workers', type=int, default=5)
    ap.add_argument('--mem-gib', type=float, default=8)
    ap.add_argument('--wall', type=float, default=3600)
    ap.add_argument('--rmax', type=int, default=301)
    ap.add_argument('--moves', default=','.join(map(str, MOVES)))
    ap.add_argument('--hints', type=int, default=8, help='per-branch root hints (0 disables)')
    args = ap.parse_args()
    out = args.out; out.mkdir(exist_ok=True)
    ledger = out / 'ledger.jsonl'
    done = set()
    solved_moves = set()
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            row = json.loads(line)
            done.add((row['m'], row['r'], row.get('mem_gib'), row.get('wall_cap')) if row['status'] != 'ok' else (row['m'], row['r']))
            if row['status'] == 'ok':
                done.add((row['m'], row['r']))
                if row['outcome'] == 'P':
                    solved_moves.add(row['m'])
    known = known_outcomes()
    moves = tuple(int(x) for x in args.moves.split(','))
    queues = {}
    for m in moves:
        q = []
        for r in range(3, args.rmax + 1, 2):
            p = minimal_generators((*W, m, r))
            if tuple(p) in known or (m, r) in done:
                continue
            if (m, r, args.mem_gib, args.wall) in done:
                continue  # already failed under these same limits
            q.append((frobenius_number(p), r, tuple(p)))
        q.sort()
        queues[m] = q
    print('queue sizes', {m: len(q) for m, q in queues.items()}, flush=True)
    order = [m for m in moves if m not in solved_moves]
    from collections import Counter
    tally = {m: Counter() for m in moves}
    for m in moves:
        for r in range(3, 1001, 2):
            mv = WINNERS.get(tuple(minimal_generators((*W, m, r))))
            if mv: tally[m][mv] += 1
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            row = json.loads(line)
            if row.get('outcome') == 'N' and row['m'] in tally:
                tally[row['m']][row['winning_move']] += 2   # recent results weigh more

    def hints_for(m):
        return [mv for mv, _ in tally[m].most_common(args.hints)] if args.hints else []
    running = {}
    turn = 0

    def next_job():
        nonlocal turn
        for _ in range(len(order)):
            m = order[turn % len(order)]; turn += 1
            if m in solved_moves or not queues[m]:
                continue
            f, r, p = queues[m].pop(0)
            return m, r, p, f
        return None

    def launch(job):
        m, r, p, f = job
        tag = f'm{m}-r{r}'
        stdout = open(out / f'{tag}.out', 'w'); stderr = open(out / f'{tag}.err', 'w')
        mem = int(args.mem_gib * 1024 ** 3)
        def cap():
            resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            os.nice(10)
        hints = [h for h in hints_for(m) if h not in p]
        binary = args.narrow_binary if args.narrow_binary and f <= 255 else args.binary
        argv = [str(binary), *(['--hints', ','.join(map(str, hints))] if hints else []), *map(str, p)]
        proc = subprocess.Popen(argv, stdout=stdout, stderr=stderr, preexec_fn=cap)
        running[proc.pid] = dict(proc=proc, m=m, r=r, p=p, f=f, start=time.monotonic(), tag=tag, files=(stdout, stderr))
        print(time.strftime('%H:%M:%S'), 'start', tag, 'F', f, 'hints', hints, flush=True)

    while True:
        if (out / 'STOP').exists() and not running:
            break
        while len(running) < args.workers and not (out / 'STOP').exists():
            job = next_job()
            if job is None:
                break
            launch(job)
        if not running:
            break
        pid, status, usage = os.wait4(-1, os.WNOHANG)
        if pid == 0:
            now = time.monotonic()
            for info in running.values():
                if now - info['start'] > args.wall and info['proc'].poll() is None:
                    info['killed'] = 'wall'
                    info['proc'].kill()
            time.sleep(1)
            continue
        info = running.pop(pid)
        for f in info['files']:
            f.close()
        code = os.waitstatus_to_exitcode(status)
        text = (out / (info['tag'] + '.out')).read_text().strip()
        row = dict(m=info['m'], r=info['r'], position=list(info['p']), frobenius=info['f'],
                   wall=time.monotonic() - info['start'], cpu=usage.ru_utime + usage.ru_stime,
                   maxrss_kb=usage.ru_maxrss, returncode=code, mem_gib=args.mem_gib, wall_cap=args.wall)
        parts = text.split()
        if code == 0 and len(parts) == 4 and parts[0] in ('P', 'N'):
            row.update(status='ok', outcome=parts[0],
                       winning_move=None if parts[1] == 'winning_move=none' else int(parts[1].split('=')[1]),
                       states=int(parts[3].split('=')[1]))
            if int(parts[2].split('=')[1]) != info['f']:
                row.update(status='frobenius-mismatch')
        else:
            row.update(status=info.get('killed') or f'failed-{code}', stderr=(out / (info['tag'] + '.err')).read_text()[-400:])
        with ledger.open('a') as fh:
            fh.write(json.dumps(row) + '\n')
        print(time.strftime('%H:%M:%S'), 'done', info['tag'], row['status'], row.get('outcome'),
              row.get('winning_move'), row.get('states'), f"{row['cpu']:.1f}s", flush=True)
        if row.get('outcome') == 'P':
            solved_moves.add(info['m'])
            (out / f'FOUND-m{info["m"]}-r{info["r"]}').write_text(json.dumps(row) + '\n')
            print('!!! FOUND P', row, flush=True)
        if row.get('outcome') == 'N' and row['m'] in tally:
            tally[row['m']][row['winning_move']] += 2


if __name__ == '__main__':
    main()
