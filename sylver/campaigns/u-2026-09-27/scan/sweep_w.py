#!/usr/bin/env python3
"""Shared-memo odd-reply sweep of one W branch with the parallel engine.

Runs ``parallel_solver --odd-list`` on batches of the branch's next
unclassified odd replies (increasing Frobenius order). One memo serves a
whole batch, so later candidates reuse the earlier ones' positions. Each
finished row is appended to the same ledger scan_w.py writes (states is
the batch's cumulative memo size). A batch that fails keeps its finished
rows; its other candidates go back to the queue. A P row stops the branch.
"""
import argparse, json, os, resource, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_w  # noqa: E402  (known_outcomes, REPO path, minimal_generators)
from sylver.short_certificates import minimal_generators  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True, help='scan directory holding ledger.jsonl')
    ap.add_argument('--parent', default='16,26,62,98')
    ap.add_argument('--move', type=int, required=True, help='0: odd replies to the parent itself')
    ap.add_argument('--binary-pattern', required=True, help='e.g. /dir/psw{words}')
    ap.add_argument('--threads', type=int, default=8)
    ap.add_argument('--batch', type=int, default=12)
    ap.add_argument('--mem-gib', type=float, default=24)
    ap.add_argument('--rmax', type=int, default=401)
    ap.add_argument('--verify', action='store_true', help='--verify-memo: rows are written after the check')
    ap.add_argument('--extra-args', default='', help='more engine options, e.g. "--max-states 1200000000" '
                    '(kunz_solver): a batch the engine ends early requeues its unfinished replies')
    args = ap.parse_args()
    ledger = args.out / 'ledger.jsonl'
    parent = tuple(int(x) for x in args.parent.split(','))
    m = args.move
    base = (*parent, m) if m else parent
    known = scan_w.known_outcomes()
    done = set()
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            row = json.loads(line)
            if row['m'] == m and row['status'] == 'ok':
                done.add(row['r'])
                if row['outcome'] == 'P':
                    print('branch already has a P row', row['r']); return
    queue = []
    for r in range(3, args.rmax + 1, 2):
        p = minimal_generators((*base, r))
        if tuple(p) in known or r in done:
            continue
        queue.append((frobenius_number(p), r, tuple(p)))
    queue.sort()
    print(time.strftime('%H:%M:%S'), 'queue', len(queue), 'first', [q[1] for q in queue[:5]], flush=True)
    mem = int(args.mem_gib * 1024 ** 3)

    def cap():
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.nice(10)
        try:  # a restartable sweep is the first victim if the host runs out of memory
            Path('/proc/self/oom_score_adj').write_text('1000')
        except OSError:
            pass

    while queue and not (args.out / 'STOP').exists():
        batch, queue = queue[:args.batch], queue[args.batch:]
        bound = max(f for f, _, _ in batch)
        binary = args.binary_pattern.format(words=bound // 64 + 1)
        replies = [r for _, r, _ in batch]
        argv = [binary, '--threads', str(args.threads), '--stop-at-p', *(['--verify-memo'] if args.verify else []),
                *args.extra_args.split(), '--odd-list', ','.join(map(str, replies)), *map(str, base)]
        tag = f'm{m}-sweep-{replies[0]}-{replies[-1]}'
        err = open(args.out / f'{tag}.err', 'w')
        start = last = time.monotonic()
        print(time.strftime('%H:%M:%S'), 'start', tag, 'bound', bound, 'engine', Path(binary).name, flush=True)
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=err, text=True, preexec_fn=cap)
        finished, found, rows, verified = set(), None, [], False
        for line in proc.stdout:
            parts = line.split()
            if parts and parts[0] == 'verified':   # the engine's last line: the memo passed its check
                verified = True
                continue
            r = int(parts[0].split('=')[1])
            f, _, p = next(item for item in batch if item[1] == r)
            now = time.monotonic()
            row = dict(m=m, r=r, position=list(p), frobenius=f, wall=now - last, returncode=None,
                       mem_gib=args.mem_gib, engine=Path(binary).name,
                       engine_args=' '.join([f'--threads {args.threads}', *args.extra_args.split(),
                                             f'--odd-list (shared memo, batch {tag})']),
                       status='ok', outcome=parts[1],
                       winning_move=None if parts[2] == 'winning_move=none' else int(parts[2].split('=')[1]),
                       states=int(parts[4].split('=')[1]), states_are='cumulative over the batch')
            if int(parts[3].split('=')[1]) != f:
                row['status'] = 'frobenius-mismatch'
            last = now
            finished.add(r)
            rows.append(row)
            print(time.strftime('%H:%M:%S'), 'done', f'm{m}-r{r}', row['status'], row['outcome'], row['winning_move'],
                  row['states'], f"{row['wall']:.1f}s", flush=True)
            if row['outcome'] == 'P':
                found = row
        code = proc.wait()
        err.close()
        for row in rows:
            row['returncode'] = code
            if args.verify:
                row['memo_verified'] = code == 0 and verified
                if not row['memo_verified'] and row['status'] == 'ok':
                    row['status'] = 'unverified'   # not counted as done; retried by a later run
        with ledger.open('a') as fh:
            for row in rows:
                fh.write(json.dumps(row) + '\n')
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        print(time.strftime('%H:%M:%S'), 'batch', tag, 'exit', code, f'{time.monotonic() - start:.1f}s wall',
              f'children cpu {usage.ru_utime + usage.ru_stime:.0f}s', flush=True)
        if found:   # verified or not, a P row stops the branch: P rows are replayed independently anyway
            (args.out / f'FOUND-m{m}-r{found["r"]}').write_text(json.dumps(found) + '\n')
            print('!!! FOUND P', found, flush=True)
            return
        unfinished = [item for item in batch if item[1] not in finished]
        if code != 0:
            print('stderr:', (args.out / f'{tag}.err').read_text()[-300:], flush=True)
            if not finished:
                print('batch made no progress; stopping', flush=True)
                return
        if unfinished:   # a failed batch, or one the engine ended early (--max-states, --stop-file)
            queue = sorted(unfinished + queue)


if __name__ == '__main__':
    main()
