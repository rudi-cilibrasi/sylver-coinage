#!/usr/bin/env python3
"""Offline protocol agent/proposer. A test double, not evidence about real LLMs."""
import json
import sys

request=json.load(sys.stdin)
usage={'input_tokens':len(json.dumps(request))//3+1,'output_tokens':100,'cost':0.}
if request.get('purpose')=='mutation':
    candidate=dict(request['parent'])
    if request['mode']=='prompt':candidate['prompt']='short-first'
    else:
        candidate['policy']=dict(candidate['policy'],batch_size=4,proof_style='witness')
    print(json.dumps({'candidate':candidate,'rationale':'offline deterministic mutation','usage':usage}))
else:
    history=request['history'];target=request['task']['manifest']['target'];info=request['task']['profile']
    prompt=request['prompt'];last=history[-1] if history else None
    if not history and 'short' not in prompt.lower():op,args='profile',{'position':target}
    elif last and last['action']['op']=='proof':op,args='submit',{'proof':last['response']['result']}
    elif last and last['response']['result'].get('outcome') in ('P','N'):
        op,args='proof',{'position':target}
    elif last and last['action']['op']=='close' and info['gcd']==1:
        op,args='exact',{'positions':[target],'seconds':.3}
    else:op,args='close',{'position':target}
    print(json.dumps({'action':{'id':len(history)+1,'op':op,'args':args},'usage':usage}))
