"""Recorded, budgeted JSON model-command adapter; proposals are never executed."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys

from .common import canonical, fields, read, sha, write
from .policies import PROMPTS


def command_response(command, request, directory, seconds, allow_network=False, credentials=()):
    """The provider executable sees system runtimes and its own files only.

    No checkout, home directory, challenge evaluator, baseline file, or referee
    directory is mounted. Request content arrives on stdin. Stdout is a single
    provider envelope. Credentials are inherited selectively, never serialized.
    """
    directory=Path(directory);directory.mkdir()
    executable=Path(command[0]).resolve()
    if not executable.is_file():raise ValueError('model command must be an absolute executable path')
    mounts={Path('/usr'),Path('/lib'),Path('/lib64'),Path('/bin')}
    # Explicit provider scripts are mounted individually, not their directory.
    provider_files=[executable]+[Path(x).resolve() for x in command[1:] if Path(x).is_file()]
    sandbox=['bwrap','--unshare-all','--die-with-parent','--new-session',
             '--proc','/proc','--dev','/dev','--tmpfs','/tmp','--chdir','/tmp']
    if allow_network:sandbox+=['--share-net']
    for path in sorted(mounts):
        if path.exists():sandbox+=['--ro-bind',str(path),str(path)]
    for path in provider_files:
        if not any(path.is_relative_to(m) for m in mounts):sandbox+=['--ro-bind',str(path),str(path)]
    if allow_network:
        for name in ('/etc/ssl','/etc/resolv.conf','/etc/hosts'):
            if Path(name).exists():sandbox+=['--ro-bind',name,name]
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8',**{k:os.environ[k] for k in credentials if k in os.environ}}
    stdout=directory/'stdout.json';stderr=directory/'stderr.txt'
    failure=None
    with stdout.open('wb') as out,stderr.open('wb') as err:
        process=subprocess.Popen([*sandbox,'--',*command],stdin=subprocess.PIPE,stdout=out,stderr=err,env=env)
        try:process.communicate(canonical(request),timeout=seconds)
        except subprocess.TimeoutExpired:
            process.kill();process.communicate();failure=ValueError('model latency limit')
        finally:
            if process.poll() is None:process.kill();process.wait()
    # A configured provider must not echo credentials. Refuse to publish leaked
    # output, retaining only digests of rejected bytes; never write secret values.
    leaked=False
    for path in (stdout,stderr):
        content=path.read_bytes()
        if any(os.environ[k].encode() in content for k in credentials if os.environ.get(k)):
            checksum=sha(content);path.write_text('REDACTED provider credential echo; sha256='+checksum+'\n')
            leaked=True
    if leaked:raise ValueError('provider echoed a credential')
    if failure:raise failure
    if process.returncode:raise ValueError('model command failed')
    return read(stdout)


def run_agent(client, config, output, seed):
    fields(config,('command','prompt','limits','model_id'),('allow_network','credentials'))
    limits=config['limits'];usage={'requests':0,'input_tokens':0,'output_tokens':0,'cost':0.,'latency_seconds':0.}
    history=[];output=Path(output)
    prompt=config['prompt']
    if prompt in PROMPTS:prompt=PROMPTS[prompt]
    for index in range(limits['requests']):
        import time
        request={'schema':1,'prompt':prompt,'seed':seed,'history':history,
                 'task':client.call('inspect'),
                 'remaining_model_budget':{'requests':limits['requests']-usage['requests'],
                    'tokens':limits['tokens']-usage['input_tokens']-usage['output_tokens'],
                    'cost':limits['cost']-usage['cost']},'instruction':'Return {action:{id,op,args},usage:{input_tokens,output_tokens,cost}}.'}
        write(output/f'model-request-{index:04d}.json',request)
        start=time.monotonic()
        usage['requests']+=1
        write(output/'model-usage.json',usage)
        try:
            envelope=command_response(config['command'],request,output/f'model-{index:04d}',limits['latency_seconds'],
                                      config.get('allow_network',False),config.get('credentials',()))
        except Exception:
            usage['unreported_usage']=True
            raise
        finally:
            usage['latency_seconds']+=time.monotonic()-start
            write(output/'model-usage.json',usage)
        fields(envelope,('action','usage'))
        fields(envelope['usage'],('input_tokens','output_tokens','cost'))
        reported=envelope['usage']
        for k in ('input_tokens','output_tokens'):
            if type(reported[k]) is not int or reported[k]<0:raise ValueError('missing or invalid provider token accounting')
        if type(reported['cost']) not in (float,int) or not math.isfinite(reported['cost']) or reported['cost']<0:
            raise ValueError('invalid provider cost')
        for k in ('input_tokens','output_tokens','cost'):usage[k]+=reported[k]
        write(output/'model-usage.json',usage)
        if usage['input_tokens']+usage['output_tokens']>limits['tokens'] or usage['cost']>limits['cost']:
            raise ValueError('model usage limit')
        action=envelope['action']
        result=client.session.request(action)
        history.append({'action':action,'response':result})
        if client.session.submitted:return
