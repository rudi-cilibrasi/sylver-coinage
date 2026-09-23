"""Training-only selection with bounded candidates, lineage, and honest failures."""
import copy
import math
from pathlib import Path
import resource
import time
import subprocess
import sys

from .agent import command_response
from .common import canonical, read, sha, write
from .episode import run_episode
from .policies import BASELINES, PROMPTS, validate_policy


def fitness(receipts):
    if not receipts or any(r.get('status')!='valid' or r.get('log_score') is None for r in receipts):
        return None  # +infinity, encoded portably rather than JSON Infinity.
    return sum(r['log_score'] for r in receipts)/len(receipts)


def selection(records,archive_size=4):
    successful=[r for r in records if r.get('fitness') is not None]
    successful.sort(key=lambda r:(r['fitness'],r['id']))
    archive=[];seen=set()
    for row in successful:
        # Distinct executable strategies, not cosmetic prompt/name duplicates.
        signature=sha({'policy':row['candidate']['policy'],'prompt':row['candidate'].get('prompt'),
                       'mode':row['candidate']['mode']})
        if signature not in seen:archive.append(row['id']);seen.add(signature)
        if len(archive)>=archive_size:break
    return {'best':successful[0]['id'] if successful else None,'archive':archive}


def mock_proposals(parent,mode):
    changed=copy.deepcopy(parent)
    if mode=='prompt':changed['prompt']='short-first'
    else:changed['policy'].update(batch_size=4,proof_style='witness',slice_seconds=.2)
    return [
        {'candidate':changed,'rationale':'reduce requests or explore witness verification tradeoff'},
        {'candidate':dict(changed,policy=dict(changed['policy'],checker='replace')),
         'rationale':'negative control: modifying the trusted checker is forbidden'},
    ]


def validate_candidate(candidate):
    if set(candidate)!={'policy','prompt','mode'} or candidate['mode'] not in ('policy','prompt'):
        raise ValueError('invalid candidate program')
    validate_policy(candidate['policy'])
    if not isinstance(candidate['prompt'],str) or len(candidate['prompt'])>8192:raise ValueError('invalid prompt')


def run_evolution(training,output,tools,seed=0,max_candidates=9,cpu_budget=120.,
                  model_requests=0,model_tokens=0,model_cost=0.,proposer=None,agent_template=None):
    """No held-out bundle or evaluator label is accepted by this function."""
    if any(b['manifest']['kind']!='training' for b in training):raise ValueError('selection accepts training only')
    if not training or max_candidates<3 or cpu_budget<=0:raise ValueError('invalid evolution budget')
    from .exact import build_tools
    build_tools(tools)
    controller_start=time.process_time();evaluation_cpu=0.;proposal_cpu=0.
    out=Path(output);out.mkdir();records=[];spent=0.;generation_cpu=0.;usage={'requests':0,'tokens':0,'cost':0.}
    plan={'schema':1,'seed':seed,'max_candidates':max_candidates,'cpu_budget':cpu_budget,
          'model_limits':{'requests':model_requests,'tokens':model_tokens,'cost':model_cost},
          'training':[sha(b['manifest']) for b in training],
          'held_out_checkpoint':'after all training selection; never used in mutation feedback'}
    write(out/'plan.json',plan)
    proposals=[{'candidate':{'policy':copy.deepcopy(p),'prompt':'default','mode':'policy'},
                'parent':None,'rationale':'baseline seed '+name} for name,p in BASELINES.items()]
    if agent_template:
        if max_candidates<5:raise ValueError('five slots required for baseline and prompt seeds')
        proposals += [{'candidate':{'policy':copy.deepcopy(BASELINES['interleaved']),'prompt':prompt,'mode':'prompt'},
                       'parent':None,'rationale':'explicit prompt seed '+prompt} for prompt in ('default','compact')]
    budget_unreconciled=False
    while len(records)<max_candidates:
        spent=evaluation_cpu+proposal_cpu+time.process_time()-controller_start
        if not proposals:
            chosen=selection(records)['best']
            if chosen is None:break  # Training panel must have a successful seed.
            parent=next(r for r in records if r['id']==chosen)
            mode='prompt' if agent_template and not any(r.get('parent') and r['candidate'].get('mode')=='prompt' for r in records) else 'policy'
            if spent>=cpu_budget:break
            start=time.process_time()
            if proposer:
                if usage['requests']>=model_requests or usage['tokens']>=model_tokens or usage['cost']>model_cost:break
                request={'purpose':'mutation','mode':mode,'seed':seed,'parent':parent['candidate'],
                         'remaining_model_budget':{'requests':model_requests-usage['requests'],
                              'tokens':model_tokens-usage['tokens'],'cost':model_cost-usage['cost']},
                         'feedback':[{'id':r['id'],'fitness':r['fitness'],'status':r['status']} for r in records]}
                work=out/f'generation-{len(records):03d}';work.mkdir()
                remaining=min(10.,cpu_budget-spent)
                cfg=work/'config.json'
                write(cfg,{'request':request,'proposer':proposer,'output':str((work/'work').resolve()),'seconds':remaining})
                control=work/'supervisor.json'
                write(control,{'command':[sys.executable,'-m','sylver.arena.propose_worker',str(cfg.resolve())],
                      'output':str((work/'accounting').resolve()),
                      'limits':{'cpu_seconds':remaining,'wall_seconds':remaining,'memory_mb':512}})
                subprocess.run([sys.executable,'-m','sylver.arena.supervisor',str(control.resolve())],check=True)
                measured=read(work/'accounting/usage.json')
                cost=measured['cpu_seconds'];proposal_cpu+=cost;spent+=cost
                usage['requests']+=1
                accounted=False
                try:
                    if measured['reason'] or measured['returncode']!=0:raise ValueError('proposer interrupted or failed')
                    envelope=read(work/'work/result.json');u=envelope['usage']
                    if any(type(u[k]) is not int or u[k]<0 for k in ('input_tokens','output_tokens')):raise ValueError('invalid proposal tokens')
                    if type(u['cost']) not in (int,float) or not math.isfinite(u['cost']) or u['cost']<0:raise ValueError('invalid proposal cost')
                    usage['tokens']+=u['input_tokens']+u['output_tokens'];usage['cost']+=u['cost'];accounted=True
                    if usage['tokens']>model_tokens or usage['cost']>model_cost:raise ValueError('proposal model budget exceeded')
                    if mode=='prompt' and envelope['candidate'].get('policy')!=parent['candidate']['policy']:
                        raise ValueError('prompt-only mutation changed policy code')
                    proposals=[{'candidate':envelope['candidate'],'rationale':envelope['rationale']}]
                except (ValueError,KeyError,TypeError) as exc:
                    records.append({'id':sha({'failure':str(exc),'index':len(records)}),'candidate':parent['candidate'],
                                    'parent':chosen,'rationale':'rejected proposer response','fitness':None,
                                    'status':'generation-invalid','error':str(exc),'runs':[]})
                    write(out/'records.json',records)
                    if not accounted:
                        usage['unreported_usage']=True
                        break
                    continue
            else:
                proposals=mock_proposals(parent['candidate'],mode)
                cost=time.process_time()-start;generation_cpu+=cost;spent+=cost
            for p in proposals:p['parent']=chosen;p['candidate']=dict(p['candidate'],mode=mode)
        proposal=proposals.pop(0);index=len(records);candidate=proposal['candidate']
        row={'id':sha({'index':index,'candidate':candidate,'seed':seed}),**proposal,'fitness':None,
             'status':'invalid','runs':[]}
        write(out/f'proposal-{index:03d}.json',proposal)
        try:
            validate_candidate(candidate)
            receipts=[]
            for task_index,bundle in enumerate(training):
                # Every candidate gets identical per-task limits. Do not run a
                # cheaper, partial-budget episode to manufacture better fitness.
                if spent+bundle['manifest']['execution']['limits']['cpu_seconds']>cpu_budget:
                    raise ValueError('total evolution CPU budget exhausted')
                path=out/f'candidate-{index:03d}-task-{task_index:03d}'
                agent=None
                if candidate['mode']=='prompt':
                    if agent_template is None:raise ValueError('prompt evolution requires an agent adapter')
                    agent=dict(agent_template,prompt=candidate['prompt'])
                receipt=run_episode(bundle,candidate['policy'],path,tools,seed,agent=agent)
                receipts.append(receipt);row['runs'].append(path.name)
                if receipt['T'] is None:
                    budget_unreconciled=True
                    raise ValueError('unmeasured episode CPU; no further budget can be released')
                evaluation_cpu+=receipt['T']
                spent=evaluation_cpu+proposal_cpu+time.process_time()-controller_start
            row['fitness']=fitness(receipts);row['status']='valid' if row['fitness'] is not None else 'unsolved'
        except (ValueError,KeyError,TypeError) as exc:row['error']=str(exc)
        records.append(row)
        write(out/'records.json',records)
        write(out/'selection.json',selection(records))
        if budget_unreconciled:break
    generation_cpu=proposal_cpu+time.process_time()-controller_start
    spent=evaluation_cpu+generation_cpu
    result={'plan':plan,'records':records,**selection(records),
            'cpu_spent':None if budget_unreconciled else spent,'measured_cpu':spent,'budget_unreconciled':budget_unreconciled,'generation_cpu':generation_cpu,'generation_model_usage':usage,
            'scope':'Training-only selection. Failed candidates retained. Recorded measurements reproduce selection; reruns have timing/model variance.'}
    write(out/'result.json',result)
    return result
