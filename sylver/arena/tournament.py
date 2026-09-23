"""Per-target leaderboards, sealed artifacts, and independent re-verification."""
from collections import defaultdict
import json
from pathlib import Path
import statistics

from .common import canonical, read, sha, write
from .episode import run_episode
from .proof import verifier_profile
from .snapshot import validate_bundle


def comparison_key(receipt):
    return (receipt['task'],receipt['baseline'],sha(receipt['verifier']),sha(receipt['execution']))


def leaderboard(entries):
    groups=defaultdict(list)
    for name,receipt in entries:
        groups[comparison_key(receipt)].append({'competitor':name,**receipt})
    result=[]
    for profile,rows in sorted(groups.items()):
        valid=sorted((r for r in rows if r['status']=='valid'),key=lambda r:(r['S'],r['agent'],r['seed']))
        failed=[r for r in rows if r['status']!='valid']
        result.append({'comparison':list(profile),'ranked':valid,'unrated':failed})
    return result


def render(entries,title='Proof-search arena'):
    lines=['# '+title,'','Scores are compared only within an identical target, snapshot, verifier, and execution profile.','',
           'C is canonical UTF-8 proof bytes; T is discovery + verification CPU seconds. Lower S=(C+100)*(T+1) is better.','']
    for group in leaderboard(entries):
        lines+=['## Target {'+','.join(map(str,(group['ranked']+group['unrated'])[0].get('position',[])))+'} — '+group['comparison'][0][:16],'',
                '| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |',
                '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        for row in group['ranked']+group['unrated']:
            values=[row['competitor'],row['status'],row.get('outcome','unknown'),row['C'],row['discovery_cpu'],row['verification_cpu'],row['T'],row['S'],row['log_score']]
            lines.append('| '+' | '.join('—' if v is None else f'{v:.6f}' if isinstance(v,float) else str(v) for v in values)+' |')
        lines.append('')
        by_agent=defaultdict(list)
        for r in group['ranked']+group['unrated']:by_agent[r['competitor']].append(r)
        for name,rows in sorted(by_agent.items()):
            scores=[r['S'] for r in rows if r['status']=='valid']
            if scores:
                lines.append(f'{name}: {len(scores)}/{len(rows)} valid; S min/median/max = '
                             f'{min(scores):.6f}/{statistics.median(scores):.6f}/{max(scores):.6f}; '
                             f'stdev = {statistics.stdev(scores) if len(scores)>1 else 0:.6f}.')
            else:lines.append(f'{name}: 0/{len(rows)} valid.')
        lines.append('')
    coverage=defaultdict(set);attempted=defaultdict(set)
    for name,r in entries:
        attempted[name].add(comparison_key(r))
        if r['status']=='valid':coverage[name].add(comparison_key(r))
    lines+=['## Coverage (separate from per-target scores)','']
    for name in sorted(attempted):lines.append(f'- {name}: {len(coverage[name])}/{len(attempted[name])} distinct tasks solved.')
    return '\n'.join(lines)+'\n'


def run_tournament(bundles,competitors,output,tools,repeats=3,seed=0):
    if type(repeats) is not int or repeats<1:raise ValueError('positive repeat count required')
    out=Path(output);out.mkdir();entries=[];runs=[]
    plan={'schema':1,'targets':[sha(b['manifest']) for b in bundles],
          'competitors':competitors,'repeats':repeats,'seed':seed,
          'order':'round-robin rotated competitors; matching profiles only'}
    write(out/'plan.json',plan)
    for repeat in range(repeats):
        order=list(competitors);shift=repeat%len(order);order=order[shift:]+order[:shift]
        for task,bundle in enumerate(bundles):
            for name in order:
                program=competitors[name]
                path=out/f'round-{repeat:02d}-task-{task:02d}-{name}'
                r=run_episode(bundle,program.get('policy'),path,tools,seed+repeat,agent=program.get('agent'))
                entries.append((name,r));runs.append({'competitor':name,'directory':path.name})
                write(out/'runs.json',runs)
                write(out/'leaderboard.json',leaderboard(entries))
                (out/'REPORT.md').write_text(render(entries))
    return entries


def reverify(episode,output,tools):
    """A new measured replay; historical discovery timing is never replaced."""
    from .episode import _phase
    episode=Path(episode);r=read(episode/'receipt.json')
    if r['status']!='valid':raise ValueError('episode has no accepted certificate')
    for name,expected in r['artifacts'].items():
        p=(episode/name).resolve()
        if not p.is_relative_to(episode.resolve()) or sha(p.read_bytes())!=expected:
            raise ValueError('artifact integrity failure')
    bundle=read(episode/'bundle.json');validate_bundle(bundle)
    if sha(bundle['manifest'])!=r['task'] or sha(bundle['snapshot'])!=r['baseline']:
        raise ValueError('pinned challenge mismatch')
    if bundle['manifest']['verifier']!=verifier_profile():raise ValueError('use the pinned verifier checkout')
    from .exact import build_tools
    binary=build_tools(tools);out=Path(output).resolve();out.mkdir();(out/'work').mkdir()
    cfg={'bundle':str((episode/'bundle.json').resolve()),'binary':str(binary),'seed':r['seed'],
         'phase':'verification','output':str(out/'work'),'limits':r['limits'],
         'submission':str((episode/'certificate.json').resolve())}
    usage=_phase(cfg,out)
    result=read(out/'work/result.json') if (out/'work/result.json').exists() else {}
    if usage['reason'] or usage['returncode']!=0 or not result.get('valid'):raise ValueError('replay failed')
    if result['C']!=r['C'] or result['certificate_sha256']!=r['verification']['certificate_sha256']:
        raise ValueError('canonical certificate changed')
    write(out/'reverification.json',{'valid':True,'historical_receipt':sha(r),'new_verification_cpu':usage['cpu_seconds'],
          'result':result,'scope':'Independent replay only. Original discovery/verification costs and scores are not replaced.'})
    return result


def verify_submission(bundle,proof,output,tools,reference_python=False):
    """Standalone accounted verification, with no fictitious discovery score."""
    from .episode import _phase
    from .exact import build_tools
    out=Path(output).resolve();out.mkdir();(out/'work').mkdir()
    validate_bundle(bundle)
    write(out/'bundle.json',bundle);write(out/'submission.json',proof)
    cfg={'bundle':str(out/'bundle.json'),'submission':str(out/'submission.json'),
         'phase':'verification','output':str(out/'work'),'binary':str(build_tools(tools)),
         'seed':0,'limits':bundle['manifest']['execution']['limits'],'reference_python':reference_python}
    usage=_phase(cfg,out)
    result=read(out/'work/result.json') if (out/'work/result.json').exists() else {}
    report={'valid':result.get('valid',False) and not usage['reason'] and usage['returncode']==0,
            'result':result,'verification_cpu':usage['cpu_seconds'],'usage':usage,
            'S':None,'reference_python':reference_python,'scope':'Verification only; discovery CPU is unknown, so no rated score.'}
    write(out/'verification.json',report)
    return report


def admit(episode,output,tools):
    """Curator operation: new immutable version after independent replay."""
    from .snapshot import snapshot, fact_id
    episode=Path(episode);bundle=read(episode/'bundle.json')
    if bundle['manifest']['kind']!='live':raise ValueError('only independently verified live discoveries may be admitted')
    out=Path(output);out.mkdir()
    native=reverify(episode,out/'native',tools)
    proof=read(episode/'certificate.json')
    python=verify_submission(bundle,proof,out/'python',tools,reference_python=True)
    if not python['valid'] or python['result']['outcome']!=native['outcome']:
        raise ValueError('independent reference replay incomplete or disagrees')
    old=bundle['snapshot'];facts=list(old['facts'].values());artifacts=dict(old['artifacts'])
    proof_hash=sha(canonical(proof));python_hash=sha((out/'python/verification.json').read_bytes())
    artifacts[proof_hash]={'kind':'new-canonical-proof'}
    artifacts[python_hash]={'kind':'independent-python-replay'}
    for k,node in proof['nodes'].items():
        if node['rule']=='baseline':continue
        p=list(map(int,k.split(',')));ident=fact_id(p,node['outcome'])
        if ident in old['facts']:continue
        children=([node['child']] if node['rule']=='edge' else
                  [r['child'] for r in node['children']] if node['rule']=='cover' else [])
        dependencies=[fact_id(list(map(int,c.split(','))),proof['nodes'][c]['outcome']) for c in children]
        facts.append({'position':p,'outcome':node['outcome'],'dependencies':dependencies,
                      'provenance':{'kind':'independently-replayed-discovery','artifacts':[proof_hash,python_hash]}})
    new=snapshot(facts,artifacts,old['theorems'])
    write(out/'snapshot.json',new);write(out/'certificate.json',proof)
    write(out/'admission.json',{'schema':1,'old_snapshot':sha(old),'new_snapshot':sha(new),
          'certificate':proof_hash,'independent_receipt':python_hash,
          'scope':'A new knowledge version for later competitions. Existing tournaments and scores are immutable.'})
    return sha(new)
