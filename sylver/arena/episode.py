"""One designated target, immutable inputs, two charged phases, exact score."""
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

from .common import ROOT, canonical, read, sha, write
from .exact import build_tools
from .policies import validate_policy
from .proof import verifier_profile
from .snapshot import validate_bundle

DEFAULT_LIMITS={'cpu_seconds':5.,'wall_seconds':15.,'memory_mb':512,
                'query_wall_seconds':1.,'protocol_calls':10000,
                'model_requests':0,'model_tokens':0,'model_cost':0.,'model_id':'none'}


def score(C,T):
    if type(C) is not int or C<0 or isinstance(T,bool) or not math.isfinite(T) or T<0:
        raise ValueError('invalid score operands')
    return (C+100)*(T+1),math.log(C+100)+math.log1p(T)


def execution_profile(limits=None):
    cpu='unknown'
    if Path('/proc/cpuinfo').exists():
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):cpu=line.split(':',1)[1].strip();break
    return {'schema':1,'platform':platform.system(),'machine':platform.machine(),
            'cpu':cpu,'python':platform.python_version(),'kernel':platform.release(),
            'libc':list(platform.libc_ver()),'logical_cpus':os.cpu_count(),
            'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
            'accounting':'linux-subreaper-wait4-aggregate-v1',
            'limits':limits or DEFAULT_LIMITS,
            'sources':{name:sha((Path(__file__).parent/name).read_bytes()) for name in
                       ('episode.py','supervisor.py','exact.py','worker.py','protocol.py','policies.py','agent.py')}}


def _phase(config,run):
    cfg=run/'config.json';write(cfg,config)
    supervisor=run/'supervisor.json'
    write(supervisor,{'command':[sys.executable,'-m','sylver.arena.worker',str(cfg)],
                      'output':str(run/'accounting'),'limits':config['limits'],'cwd':str(ROOT)})
    # All phase outputs/inputs are fixed before process execution. Policy
    # programs cannot mutate them: only the trusted worker interprets the DSL.
    process=subprocess.Popen([sys.executable,'-m','sylver.arena.supervisor',str(supervisor)],cwd=ROOT)
    try:code=process.wait()
    except BaseException:
        process.terminate();process.wait();raise
    usage=run/'accounting/usage.json'
    return read(usage) if code==0 and usage.exists() else {'reason':'accounting-incomplete','cpu_seconds':None}


def run_episode(bundle,policy,output,tools,seed=0,script=None,agent=None):
    validate_bundle(bundle)
    if bundle['manifest']['verifier']!=verifier_profile():raise ValueError('verifier profile changed')
    limits=bundle['manifest']['execution']['limits']
    if bundle['manifest']['execution']!=execution_profile(limits):raise ValueError('execution profile mismatch')
    if policy is not None:validate_policy(policy)
    if agent is not None:
        if agent.get('model_id')!=limits['model_id']:raise ValueError('agent model differs from the fixed execution profile')
        ml=agent['limits']
        if (ml['requests']>limits['model_requests'] or ml['tokens']>limits['model_tokens'] or ml['cost']>limits['model_cost']):
            raise ValueError('agent exceeds fixed model profile')
    binary=build_tools(tools)  # Shared build is outside rated episodes.
    output=Path(output).resolve();output.mkdir()  # No free overwrite/restart.
    write(output/'bundle.json',bundle)
    competitor={'policy':policy,'seed':seed,'script':script,'agent':agent}
    write(output/'competitor.json',competitor)
    receipt={'schema':1,'status':'incomplete','task':sha(bundle['manifest']),
             'baseline':sha(bundle['snapshot']),'agent':sha(competitor),'seed':seed,
             'position':bundle['manifest']['target'],'kind':bundle['manifest']['kind'],
             'native_binary_sha256':sha(binary.read_bytes()),
             'reproduce':'python -m sylver.arena verify EPISODE_DIRECTORY --output NEW_DIRECTORY',
             'verifier':bundle['manifest']['verifier'],'execution':bundle['manifest']['execution'],
             'limits':limits,'discovery_cpu':None,'verification_cpu':None,'T':None,'C':None,
             'S':None,'log_score':None,'model_usage':None,'phases':{}}
    write(output/'receipt.json',receipt)
    config={'bundle':str(output/'bundle.json'),'binary':str(binary),'seed':seed}
    if agent is not None:config['agent']=agent
    elif script is not None:config['script']=script
    else:config['policy']=policy
    return _execute(output,bundle,binary,competitor,receipt)


def _execute(output,bundle,binary,competitor,receipt,resuming=False,expected_receipt=None):
    import fcntl
    with (output/'.episode.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('episode is already running')
        if expected_receipt is not None and sha(read(output/'receipt.json'))!=expected_receipt:
            raise ValueError('episode changed while preparing resume')
        if resuming:write(output/f'receipt-before-resume-{receipt.get("attempts",1):04d}.json',receipt)
        return _execute_locked(output,bundle,binary,competitor,receipt,resuming)


def _execute_locked(output,bundle,binary,competitor,receipt,resuming=False):
    limits=receipt['limits']
    used_cpu=sum(r['cpu_seconds'] for r in receipt['phases'].values())
    used_wall=sum(r['wall_seconds'] for r in receipt['phases'].values())
    attempt=receipt.get('attempts',0);receipt['attempts']=attempt+1
    attempt_root=output if attempt==0 else output/f'attempt-{attempt:04d}'
    if attempt:attempt_root.mkdir()
    config={'bundle':str(output/'bundle.json'),'binary':str(binary),'seed':receipt['seed']}
    for name in ('agent','script','policy'):
        if competitor[name] is not None:config[name]=competitor[name];break
    if resuming and receipt.get('checkpoint'):
        config['resume_nodes']=str(output/receipt['checkpoint'])
    receipt.update(status='incomplete',C=None,S=None,log_score=None,T=None)
    write(output/'receipt.json',receipt)
    try:
        phases=('verification',) if resuming and (output/'submission.json').exists() else ('discovery','verification')
        for phase in phases:
            run=attempt_root/phase;run.mkdir();work=run/'work';work.mkdir()
            remaining=dict(limits,cpu_seconds=limits['cpu_seconds']-used_cpu,
                           wall_seconds=limits['wall_seconds']-used_wall)
            if min(remaining['cpu_seconds'],remaining['wall_seconds'])<=0:
                receipt['status']='over-budget';break
            cfg=dict(config,phase=phase,output=str(work),limits=remaining)
            if phase=='verification':cfg['submission']=str(output/'submission.json')
            usage=_phase(cfg,run)
            phase_key=str(run.relative_to(output));receipt['phases'][phase_key]=usage
            receipt[phase+'_cpu']=sum(x['cpu_seconds'] for k,x in receipt['phases'].items()
                                      if k.split('/')[-1]==phase and x['cpu_seconds'] is not None)
            if usage['cpu_seconds'] is None:
                receipt['status']='accounting-incomplete';break
            used_cpu+=usage['cpu_seconds'];used_wall+=usage['wall_seconds']
            result=read(work/'result.json') if (work/'result.json').exists() else {}
            if (work/'known-nodes.json').exists():receipt['checkpoint']=str((work/'known-nodes.json').relative_to(output))
            if (work/'model-usage.json').exists():
                previous=receipt.get('model_usage') or {'requests':0,'input_tokens':0,'output_tokens':0,'cost':0.,'latency_seconds':0.}
                current=read(work/'model-usage.json')
                for k,v in current.items():previous[k]=previous.get(k,0)+v
                receipt['model_usage']=previous
            if usage['reason'] or usage['returncode']!=0:
                receipt['status']=usage['reason'] or 'invalid';receipt['failure']=result.get('error','worker failed');break
            if phase=='discovery':
                if result.get('status')!='submitted':receipt['status']=result.get('status','unsolved');break
                (output/'submission.json').write_bytes((work/'submission.json').read_bytes())
            elif result.get('valid'):
                receipt.update(status='valid',C=result['C'],outcome=result['outcome'],verification=result)
                (output/'certificate.json').write_bytes((work/'certificate.json').read_bytes())
        receipt['T']=used_cpu if all(x['cpu_seconds'] is not None for x in receipt['phases'].values()) else None
        if receipt['status']=='valid' and used_cpu<=limits['cpu_seconds'] and used_wall<=limits['wall_seconds']:
            receipt['S'],receipt['log_score']=score(receipt['C'],used_cpu)
        elif receipt['status']=='valid':receipt['status']='over-budget'
    except BaseException:
        receipt['status']='cancelled'
        # Reconcile interrupted phases before permitting any future continuation.
        for usage_path in output.glob('**/accounting/usage.json'):
            run=usage_path.parent.parent;usage=read(usage_path)
            receipt['phases'][str(run.relative_to(output))]=usage
            checkpoint=run/'work/known-nodes.json'
            if checkpoint.exists():receipt['checkpoint']=str(checkpoint.relative_to(output))
        for phase in ('discovery','verification'):
            receipt[phase+'_cpu']=sum(r['cpu_seconds'] for k,r in receipt['phases'].items() if k.split('/')[-1]==phase)
        receipt['T']=sum(r['cpu_seconds'] for r in receipt['phases'].values()) if receipt['phases'] else None
        raise
    finally:
        receipt['artifacts']={str(p.relative_to(output)):sha(p.read_bytes()) for p in output.rglob('*')
                              if p.is_file() and p!=output/'receipt.json' and p.suffix!='.tmp'}
        write(output/'receipt.json',receipt)
    return receipt


def resume_episode(output,tools=None):
    """Continue only with reconciled costs; retain every prior charged phase."""
    output=Path(output).resolve();receipt=read(output/'receipt.json');original_receipt=sha(receipt)
    if receipt['status'] not in ('cancelled','unsolved','incomplete'):
        raise ValueError('episode is sealed or has an unrecoverable failure: '+receipt['status'])
    # Never treat a missing handle/receipt as a free completed phase. Every
    # launched phase must have authoritative, final wait4 accounting.
    for phase in output.glob('**/supervisor.json'):
        usage_path=phase.parent/'accounting/usage.json'
        if not usage_path.exists():raise ValueError('cannot resume with unmeasured CPU')
        usage=read(usage_path)
        receipt['phases'][str(phase.parent.relative_to(output))]=usage
    if any(r['cpu_seconds'] is None for r in receipt['phases'].values()):raise ValueError('unmeasured CPU')
    for name,expected in receipt['artifacts'].items():
        path=(output/name).resolve()
        if not path.is_relative_to(output) or sha(path.read_bytes())!=expected:raise ValueError('episode inputs/artifacts changed')
    bundle=read(output/'bundle.json');competitor=read(output/'competitor.json');validate_bundle(bundle)
    if sha(bundle['manifest'])!=receipt['task'] or sha(competitor)!=receipt['agent']:raise ValueError('resumed identity changed')
    if bundle['manifest']['verifier']!=verifier_profile() or bundle['manifest']['execution']!=execution_profile(receipt['limits']):
        raise ValueError('cannot resume under a different execution profile')
    if receipt.get('model_usage'):
        # Unknown provider usage, or a model continuation requiring fresh quota,
        # cannot silently restart. Recorded deterministic policy runs can resume.
        raise ValueError('model episodes are sealed; resume cannot reset provider budgets')
    if sum(r['cpu_seconds'] for r in receipt['phases'].values())>=receipt['limits']['cpu_seconds']:
        raise ValueError('CPU budget exhausted')
    return _execute(output,bundle,build_tools(tools or output/'tools'),competitor,receipt,True,original_receipt)
