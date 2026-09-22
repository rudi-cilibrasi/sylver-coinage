#!/usr/bin/env python3
"""Bounded, interleaved finite witness search on W's remaining branches.

The exact native solver is unchanged. A killed batch contributes only complete
flushed rows; only its first unfinished request is charged an unsuccessful
attempt. Later requests remain unattempted. No finite prefix proves an even
position P. An observed P witness stops this discovery pass for fresh replay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'sylver/publication/plan2-2026-09-05'))
from sylver.focus_campaign import restore
from sylver.proof_graph import key, position
from sylver.reconcile_campaign import audit_derived
from sylver.short_certificates import minimal_generators, is_generated
from sylver.solver import frobenius_number

W = (16, 26, 62, 98)
MOVES = (70, 86, 92, 102, 108, 118, 134)
ROW = re.compile(r'position=([\d,]+) ([PN]) winning_move=(none|\d+) '
                 r'frobenius=(\d+) cumulative_states=(\d+)')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def parse_rows(path, positions):
    rows = []
    for line in path.read_text().splitlines():
        match = ROW.fullmatch(line)
        if match is None:
            raise ValueError(f'malformed output: {line}')
        k, outcome, winner, f, states = match.groups()
        gs = tuple(map(int, k.split(',')))
        move = None if winner == 'none' else int(winner)
        if (len(rows) >= len(positions) or gs != positions[len(rows)]
                or int(f) != frobenius_number(gs)
                or (outcome == 'P') != (move is None)
                or rows and int(states) < rows[-1]['cumulative_states']
                or move is not None and (move < 2 or is_generated(gs, move))):
            raise ValueError(f'invalid output: {line}')
        rows.append(dict(position=gs, outcome=outcome, winning_move=move,
                         frobenius=int(f), cumulative_states=int(states)))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--budget', type=float, default=3600)
    parser.add_argument('--slice', type=float, default=90)
    parser.add_argument('--odd-limit', type=int, default=301)
    parser.add_argument('--memory-gib', type=int, default=8)
    args = parser.parse_args()
    if min(args.budget, args.slice, args.memory_gib) <= 0 or args.odd_limit < 3:
        parser.error('invalid limits')
    out = args.output.resolve()
    out.mkdir()  # Never overwrite an earlier campaign.
    seed = ROOT / 'sylver/campaigns/targeted-2026-09-22/short56/proof-graph.json'
    graph, seed_hash = restore(seed)
    extras = []
    for name in ('b76-even', 'b76-reply36-46'):
        path = seed.parent.parent / name / 'proof-graph.json'
        extra, checksum = restore(path)
        for k, fact in extra.facts.items():
            if fact['evidence']['kind'] != 'exact-cache':
                graph.add_fact(position(k), fact['outcome'], fact['evidence'])
        extras.append({'path': str(path.relative_to(ROOT)), 'sha256': checksum})
    source = ROOT / 'sylver/native_solver.cpp'
    source_hash = digest(source)
    initial = graph.inspect(W)
    if initial['outcome'] != 'unknown' or initial['open_moves'] != list(MOVES):
        raise ValueError(f'unexpected starting frontier: {initial}')
    save(out / 'inputs.json', {
        'seed': str(seed.relative_to(ROOT)), 'seed_sha256': seed_hash,
        'extra_graphs': extras, 'source_sha256': source_hash,
        'runner_sha256': digest(Path(__file__)), 'budget_seconds': args.budget,
        'slice_seconds': args.slice, 'odd_limit': args.odd_limit,
        'memory_gib': args.memory_gib, 'moves': MOVES,
        'schedule': 'Two rounds of one candidate per branch, rotating the first branch. '
                    'Within each branch: unsuccessful attempts, Frobenius, position. '
                    'Only the first unfinished row is deferred after interruption.',
    })
    candidates = {}
    for m in MOVES:
        candidates[m] = sorted({minimal_generators((*W, m, odd))
                                for odd in range(3, args.odd_limit + 1, 2)},
                               key=lambda p: (frobenius_number(p), p))
    failures = {}
    receipts = []
    elapsed = 0.0
    found = []
    build = out / 'build'
    build.mkdir()

    def checkpoint():
        graph.close([W, *(minimal_generators((*W, m)) for m in MOVES)])
        node = graph.inspect(W)
        result = {'target': W, 'outcome': node['outcome'],
                  'open_moves': node.get('open_moves', []),
                  'native_elapsed_seconds': elapsed, 'batches': len(receipts),
                  'completed_queries': sum(r['completed'] for r in receipts),
                  'failed_attempts': failures, 'P_candidates': found,
                  'audit': audit_derived(graph),
                  'scope': 'Discovery ledger. Complete rows are exact native results; '
                           'new P witnesses require fresh replay. Inherited facts keep '
                           'their dependencies. Timeouts and finite prefixes are unknown.'}
        graph.export(out / 'proof-graph.tmp', result)
        (out / 'proof-graph.tmp').replace(out / 'proof-graph.json')
        save(out / 'frontier.json', result)
        print('FRONTIER', result['open_moves'], 'seconds', round(elapsed, 2),
              'completed', result['completed_queries'], flush=True)

    checkpoint()
    while elapsed < args.budget and not found:
        queues = {}
        for m in MOVES:
            if graph.route((*W, m)):
                continue
            queues[m] = sorted((p for p in candidates[m] if not graph.route(p)),
                               key=lambda p: (failures.get(key(p), 0),
                                              frobenius_number(p), p))
        rotation = len(receipts) % len(MOVES)
        order = MOVES[rotation:] + MOVES[:rotation]
        positions = []
        for depth in range(2):
            for m in order:
                q = queues.get(m, [])
                if len(q) > depth and q[depth] not in positions:
                    positions.append(q[depth])
        if not positions:
            break
        run = out / f'batch-{len(receipts) + 1:04d}'
        run.mkdir()
        requests = run / 'positions.txt'
        requests.write_text('\n'.join(map(key, positions)) + '\n')
        words = max(map(frobenius_number, positions)) // 64 + 1
        binary = build / f'native-{source_hash[:16]}-w{words}'
        if not binary.exists():
            subprocess.run(['g++', '-std=c++20', '-O3', '-Wall', '-Wextra',
                            '-pedantic', f'-DSYLVER_NATIVE_WORDS={words}',
                            str(source), '-o', str(binary)], check=True)
        limit = min(args.slice, args.budget - elapsed)
        command = [str(binary), '--batch-file', str(requests)]

        def cap():
            resource.setrlimit(resource.RLIMIT_AS, (args.memory_gib * 1024**3,) * 2)
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

        stdout, stderr = run / 'stdout.txt', run / 'stderr.txt'
        start = time.monotonic()
        reason = 'completed'
        with stdout.open('w') as output, stderr.open('w') as errors:
            process = subprocess.Popen(command, stdout=output, stderr=errors,
                                       preexec_fn=cap)
            print('BATCH', len(receipts) + 1, 'pid', process.pid,
                  'first', key(positions[0]), 'limit', round(limit, 2), flush=True)
            try:
                while process.poll() is None:
                    if ' P winning_move=none ' in stdout.read_text():
                        reason = 'P-found'
                        process.kill()
                        break
                    if time.monotonic() - start >= limit:
                        reason = 'timeout'
                        process.kill()
                        break
                    time.sleep(0.2)
                process.wait()
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        duration = time.monotonic() - start
        elapsed += duration
        rows = parse_rows(stdout, positions)
        if process.returncode == 0 and len(rows) != len(positions):
            raise ValueError('successful process omitted results')
        if process.returncode != 0 and reason == 'completed':
            reason = 'process-error'
        for row in rows:
            gs = tuple(row['position'])
            ev = {'kind': 'native-batch', 'source': str(stdout),
                  'source_sha256': source_hash, 'stdout_sha256': digest(stdout),
                  'native_words': words, **row}
            graph.add_fact(gs, row['outcome'], ev)
            if row['winning_move'] is not None:
                graph.add_fact((*gs, row['winning_move']), 'P', {
                    **ev, 'kind': 'native-batch-winning-destination', 'parent': key(gs)})
            if row['outcome'] == 'P':
                found.append(row)
            print('RESULT', key(gs), row['outcome'], row['winning_move'], flush=True)
        if len(rows) < len(positions) and not found:
            blocked = key(positions[len(rows)])
            failures[blocked] = failures.get(blocked, 0) + 1
        receipt = {'command': command, 'source_sha256': source_hash,
                   'binary_sha256': digest(binary), 'native_words': words,
                   'requests_sha256': digest(requests), 'stdout_sha256': digest(stdout),
                   'stderr_sha256': digest(stderr), 'seconds_limit': limit,
                   'elapsed_seconds': duration, 'returncode': process.returncode,
                   'stop_reason': reason, 'requested': len(positions),
                   'completed': len(rows), 'rows': rows}
        save(run / 'receipt.json', receipt)
        receipts.append(receipt)
        checkpoint()
        if reason == 'process-error':
            raise RuntimeError(f'native process failed; see {stderr}')


if __name__ == '__main__':
    main()
