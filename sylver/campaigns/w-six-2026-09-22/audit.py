#!/usr/bin/env python3
"""Audit campaign bookkeeping and report the remaining finite-search frontier.

This checks hashes, legal destinations, structural deductions, and accounting;
it does not independently replay native finite evaluations.
"""
import argparse
import json
from pathlib import Path

from search import (ROOT, W, MOVES, audit_derived, digest, key,
                    minimal_generators, parse_rows, restore, save)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    out = args.evidence.resolve()
    manifest = json.loads((out / 'inputs.json').read_text())
    assert digest(ROOT / manifest['seed']) == manifest['seed_sha256']
    assert any(digest(Path(__file__).with_name(name)) == manifest['runner_sha256']
               for name in ('search.py',))
    assert digest(ROOT / 'sylver/native_solver.cpp') == manifest['source_sha256']
    for item in manifest['extra_graphs']:
        assert digest(ROOT / item['path']) == item['sha256']
    graph, graph_hash = restore(out / 'proof-graph.json')
    frontier = json.loads((out / 'frontier.json').read_text())
    completed, failures, elapsed, states = {}, {}, 0.0, 0
    receipts = sorted(out.glob('batch-*/receipt.json'))
    for receipt_path in receipts:
        run = receipt_path.parent
        receipt = json.loads(receipt_path.read_text())
        assert receipt['source_sha256'] == manifest['source_sha256']
        for name, field in [('positions.txt', 'requests_sha256'),
                            ('stdout.txt', 'stdout_sha256'),
                            ('stderr.txt', 'stderr_sha256')]:
            assert digest(run / name) == receipt[field]
        positions = [tuple(map(int, s.split(',')))
                     for s in (run / 'positions.txt').read_text().splitlines()]
        rows = parse_rows(run / 'stdout.txt', positions)
        assert json.loads(json.dumps(rows)) == receipt['rows']
        assert len(rows) == receipt['completed']
        assert len(positions) == receipt['requested']
        assert receipt['elapsed_seconds'] <= receipt['seconds_limit'] + 5
        for row in rows:
            k = key(row['position'])
            assert k not in completed
            assert graph.facts[k]['outcome'] == row['outcome']
            assert graph.facts[k]['evidence']['stdout_sha256'] == receipt['stdout_sha256']
            completed[k] = row
            if row['winning_move'] is not None:
                dest = key((*row['position'], row['winning_move']))
                assert graph.facts[dest]['outcome'] == 'P'
        if len(rows) < len(positions) and not any(r['outcome'] == 'P' for r in rows):
            k = key(positions[len(rows)])
            failures[k] = failures.get(k, 0) + 1
        elapsed += receipt['elapsed_seconds']
        states += rows[-1]['cumulative_states'] if rows else 0
    assert failures == frontier['failed_attempts']
    assert len(completed) == frontier['completed_queries']
    assert len(receipts) == frontier['batches']
    assert abs(elapsed - frontier['native_elapsed_seconds']) < 1e-6
    assert elapsed <= manifest['budget_seconds'] + 5
    node = graph.inspect(W)
    assert node['outcome'] == frontier['outcome']
    assert node.get('open_moves', []) == frontier['open_moves']
    branches = []
    for m in MOVES:
        unknown, winning = [], []
        for odd in range(3, manifest['odd_limit'] + 1, 2):
            p = minimal_generators((*W, m, odd))
            fact = graph.route(p)
            if not fact:
                unknown.append(odd)
            elif fact['outcome'] == 'P':
                winning.append(odd)
        branches.append({'move': m, 'outcome': graph.inspect((*W, m))['outcome'],
                         'first_unknown_odd': unknown[0] if unknown else None,
                         'unknown_odds_through_limit': unknown,
                         'P_witnesses': winning})
    result = {'status': 'bookkeeping-and-structure-verified',
              'source_sha256': manifest['source_sha256'], 'graph_sha256': graph_hash,
              'native_elapsed_seconds': elapsed, 'completed_queries': len(completed),
              'P_queries': [r for r in completed.values() if r['outcome'] == 'P'],
              'last_completed_state_counts_sum': states,
              'state_count_scope': 'Sum of last completed cumulative counts per batch; '
                                   'overlaps across batches and omits unfinished work.',
              'audit': audit_derived(graph), 'branches': branches,
              'scope': __doc__}
    if args.output:
        save(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'branches'}, indent=2))
    for branch in branches:
        print('MOVE', branch['move'], 'first unknown', branch['first_unknown_odd'],
              'P witnesses', branch['P_witnesses'])


if __name__ == '__main__':
    main()
