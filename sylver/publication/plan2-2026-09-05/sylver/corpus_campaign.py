"""Verify the distinct finite destinations claimed by an attributed corpus.

Claims select work; they never become facts without an exact result or a
complete proof graph. Outputs inherit the privacy of the input corpus.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from sylver.focus_campaign import restore
from sylver.proof_graph import key, position, profile
from sylver.reconcile_campaign import ExactChecks, audit_derived, claim_target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--claims', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--exact-budget', type=float, default=600)
    parser.add_argument('--seconds', type=float, default=2)
    parser.add_argument('--max-frobenius', type=int, default=149)
    parser.add_argument('--retry-timeouts', action='store_true')
    args = parser.parse_args()
    if args.exact_budget < 0 or args.seconds <= 0:
        parser.error('budget must be nonnegative and seconds positive')
    args.output.mkdir(parents=True, exist_ok=True)
    graph, digest = restore(args.seed)
    raw = args.claims.read_bytes()
    claims = json.loads(raw)['claims']
    manifest = {'seed': str(args.seed.resolve()), 'seed_sha256': digest,
                'claims': str(args.claims.resolve()), 'claims_sha256': hashlib.sha256(raw).hexdigest()}
    path = args.output / 'inputs.json'
    if path.exists() and json.loads(path.read_text()) != manifest:
        raise ValueError('output directory belongs to different inputs')
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    checker = ExactChecks(graph, args.output, args.exact_budget, args.retry_timeouts)
    destinations = {claim_target(c) for c in claims}
    destinations.discard(None)
    targets = {p for p in destinations if profile(p)['gcd'] != 1}
    targets.update(position(k) for k in graph.nodes)
    jobs = sorted((p for p in destinations if profile(p)['gcd'] == 1
                   and profile(p)['frobenius'] <= min(1023, args.max_frobenius)),
                  key=lambda p: (profile(p)['frobenius'], -len(p), p))

    def checkpoint():
        graph.close(targets)
        verified = []
        for claim in claims:
            dest = claim_target(claim)
            fact = graph.facts.get(key(dest)) if dest else None
            status = ('illegal-reply' if dest is None else 'pending' if fact is None
                      else 'verified' if fact['outcome'] == 'P' else 'contradicted')
            verified.append({**claim, 'target': dest, 'verification': status})
        counts = dict(Counter(c['verification'] for c in verified))
        graph.export(args.output / 'proof-graph.tmp', {
            **manifest, 'claim_counts': counts, 'budget_remaining': checker.remaining,
            'derived_step_audit': audit_derived(graph),
            'max_frobenius': args.max_frobenius, 'per_check_seconds': args.seconds})
        (args.output / 'proof-graph.tmp').replace(args.output / 'proof-graph.json')
        (args.output / 'verified-claims.json').write_text(json.dumps(verified, indent=2) + '\n')
        print('CORPUS', counts, 'budget', round(checker.remaining, 1), flush=True)

    checkpoint()
    attempted = 0
    for job in jobs:
        if checker.remaining <= 0:
            break
        if graph.route(job) or key(job) in checker.attempted:
            continue
        result = checker.solve(job, args.seconds)
        attempted += 1
        print('CHECK', key(job), result['outcome'] if result else 'unknown', flush=True)
        if attempted % 25 == 0:
            checkpoint()
    checkpoint()


if __name__ == '__main__':
    main()
