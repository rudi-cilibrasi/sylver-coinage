"""Offline reproducible pilot: fixed training selection, then sealed held-out test."""
import copy
from pathlib import Path

from .common import ROOT, read, sha, write
from .episode import DEFAULT_LIMITS
from .evolution import run_evolution
from .fixtures import build_fixtures
from .policies import BASELINES
from .tournament import render, run_tournament


def mock_agent(prompt='default'):
    return {'command':['/usr/bin/python3',str(ROOT/'sylver/arena/mock_provider.py')],
            'model_id':'offline-mock-v1','prompt':prompt,'limits':{'requests':12,'tokens':20000,'cost':0.,'latency_seconds':3.}}


def pilot(output,repeats=3,seed=0):
    out=Path(output);out.mkdir()
    limits=dict(DEFAULT_LIMITS,model_requests=12,model_tokens=20000,model_id='offline-mock-v1')
    index=build_fixtures(out/'fixtures',limits)
    load=lambda kind:[read(out/'fixtures/visible'/(name+'.json')) for name in index[kind]]
    write(out/'predeclared-plan.json',{'schema':1,'seed':seed,'repeats':repeats,
          'training':index['training'],'held-out':index['held-out'],
          'checkpoint':'held-out only after all training selection; no further mutation',
          'evolution_candidates':9,'evolution_cpu_budget':120.,
          'model':'offline scripted test double; no remote calls or API spending'})
    evolution=run_evolution(load('training'),out/'evolution',out/'tools',seed,max_candidates=9,
                            cpu_budget=120.,agent_template=mock_agent())
    competitors={name:{'policy':p} for name,p in BASELINES.items()}
    competitors['mock-prompt-seed']={'agent':mock_agent()}
    for mode in ('policy','prompt'):
        rows=[r for r in evolution['records'] if r['parent'] and r['candidate']['mode']==mode and r['fitness'] is not None]
        if rows:
            winner=min(rows,key=lambda r:(r['fitness'],r['id']))
            competitors['evolved-'+mode]=({'policy':winner['candidate']['policy']} if mode=='policy' else
                                           {'agent':mock_agent(winner['candidate']['prompt'])})
    # Selection is now sealed. Neither these held-out receipts nor labels are
    # ever passed to run_evolution/proposer. The evaluator checks only afterward.
    write(out/'selected.json',{'training_result_sha256':sha(evolution),'competitors':competitors})
    training=run_tournament(load('training'),competitors,out/'training',out/'tools',repeats,seed)
    held=run_tournament(load('held-out'),competitors,out/'held-out',out/'tools',repeats,seed)
    labels=read(out/'fixtures/evaluator/labels.json')
    expected={sha(read(out/'fixtures/visible'/(name+'.json'))['manifest']):label for name,label in labels.items()}
    for _,r in training+held:
        if r['status']=='valid' and r['outcome']!=expected[r['task']]:raise ValueError('held-out label disagreement')
    report='''# Proof-search arena pilot

This is an offline implementation pilot with a scripted model test double.
It measures local strategies and protocol overhead; it is not evidence that
real language-model prompt evolution improves mathematical search.

The training panel, held-out checkpoint, seed, repeats, CPU/model limits,
and nine-candidate cap were declared before evaluation. All deployments
use identical per-task profiles. Generation overhead is separate from each
candidate's episode score. No hidden outcomes or proofs enter selection.

'''
    report+=f"Evolution spent {evolution['cpu_spent']:.6f} CPU seconds including candidate evaluations; "
    report+=f"proposal generation accounted for {evolution['generation_cpu']:.6f} seconds. "
    report+='Remote requests, tokens, and spending: zero. Local mock-provider usage is in episode receipts.\n\n'
    report+='## Candidate history\n\n| Candidate | Mode | Status | Mean log(S), training | Parent |\n| --- | --- | --- | ---: | --- |\n'
    for row in evolution['records']:
        report+=f"| {row['id'][:12]} | {row['candidate']['mode']} | {row['status']} | {row['fitness']} | {(row['parent'] or 'seed')[:12]} |\n"
    report+='\n'+render(training,'Training repetitions')+'\n'+render(held,'Held-out repetitions')
    from collections import defaultdict
    from statistics import median
    groups=defaultdict(lambda:defaultdict(list))
    for name,r in held:
        if r['status']=='valid':groups[r['task']][name].append(r['S'])
    report+='\n## Per-target held-out comparison\n\n'
    for evolved,baseline in (('evolved-policy','interleaved'),('evolved-prompt','mock-prompt-seed')):
        pairs=[(median(rows[evolved]),median(rows[baseline])) for rows in groups.values() if rows[evolved] and rows[baseline]]
        wins=sum(a<b for a,b in pairs)
        report+=f'{evolved}: lower median S than {baseline} on {wins}/{len(pairs)} comparable held-out targets; no cross-target raw-score sum.\n\n'
    report+='''
## Decision: revise before a live evolutionary campaign

The harness compares valid proofs, rejects malformed proposals, and retains
failures and timing distributions. These small, public finite/short fixtures
are an engineering control, and timing differences can be dominated by
process startup. The prompt arm uses a deterministic script, not an LLM.
Consequently this pilot does not establish a reproducible evolutionary search
advantage on difficult W branches. Keep the fixed verifier/accounting and
expand the predeclared training panel before spending on remote-model/live
search. Do not select a winner using this held-out report.

No new live discovery was attempted or admitted. W's current five unresolved
moves are 70,86,92,108,118. The original six post-PR5 challenges also include
102, now a public regression because PR13 published reply 95. Resolving W
would imply Q N; U P still also requires X N. Opening 16 remains unresolved.

Reproduce with `python -m sylver.arena pilot --output /tmp/arena-pilot`.
Use the recorded seed and repeat count for another run. Selection can be
replayed exactly from recorded measurements; wall/CPU timings and remote
model responses are not promised bitwise reproducible. Each episode includes
a bundle, policy/agent manifest, canonical certificate, protocol/model
transcripts, hashes, CPU receipts, and an independent replay command.
'''
    (out/'REPORT.md').write_text(report)
    return evolution
