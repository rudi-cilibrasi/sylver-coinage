"""Bounded declarative policy programs; no competitor eval/import/file access."""
import random
from .common import fields, key, position, profile

BASELINES={
    'increasing':{'strategy':'increasing','batch_size':1,'odd_limit':65,'slice_seconds':.3,'rounds':12,'subsidiary_depth':0,'proof_style':'compact'},
    'interleaved':{'strategy':'interleaved','batch_size':8,'odd_limit':65,'slice_seconds':.6,'rounds':12,'subsidiary_depth':0,'proof_style':'compact'},
    'routes-short':{'strategy':'routes-short','batch_size':8,'odd_limit':65,'slice_seconds':.6,'rounds':12,'subsidiary_depth':2,'proof_style':'compact'},
}
PROMPTS={
    'default':'Use exact routing first. Submit only supported proofs. Unknown is not P.',
    'short-first':'Inspect complete short covers before spending on finite witness searches.',
    'compact':'Prefer a small proof, while accounting for its full fresh verification cost.',
}


def validate_policy(policy):
    fields(policy,('strategy','batch_size','odd_limit','slice_seconds','rounds','subsidiary_depth','proof_style'))
    if policy['strategy'] not in ('increasing','interleaved','routes-short'):raise ValueError('unsupported policy program')
    for name,lo,hi in (('batch_size',1,128),('odd_limit',3,1023),('rounds',1,1000),('subsidiary_depth',0,3)):
        if type(policy[name]) is not int or not lo<=policy[name]<=hi:raise ValueError('policy limit outside profile')
    if type(policy['slice_seconds']) not in (int,float) or not 0<policy['slice_seconds']<=300:raise ValueError('invalid slice')
    if policy['proof_style'] not in ('compact','witness'):raise ValueError('invalid proof style')
    return policy


def run_policy(client,policy,seed=0):
    validate_policy(policy)
    random.Random(seed)  # Pin seed even for these deterministic baselines.
    target=tuple(client.call('inspect')['manifest']['target'])
    subsidiary={target};frontier=[target]
    if policy['strategy']=='routes-short':
        for _ in range(policy['subsidiary_depth']):
            following=[]
            for p in frontier:
                info=client.call('profile',position=p)
                for m in info.get('even_moves',[]):
                    q=position((*p,m));qi=client.call('profile',position=q)
                    if qi['complete'] and q not in subsidiary:
                        subsidiary.add(q);following.append(q)
            frontier=following
    failures={};attempted=set()
    for turn in range(policy['rounds']):
        for p in sorted(subsidiary,key=lambda p:(-len(p),p)):
            client.call('close',position=p)
        if client.call('route',position=target)['outcome']!='unknown':
            client.call('submit',proof=client.call('proof',position=target));return
        queues=[]
        for p in sorted(subsidiary):
            if client.call('lookup',position=p)['outcome']!='unknown':continue
            info=client.call('profile',position=p)
            candidates=[p] if info['gcd']==1 else []
            candidates.extend(position((*p,m)) for m in
                              (info['moves'] if info['complete'] else range(3,policy['odd_limit']+1,2)))
            queue=[]
            for q in dict.fromkeys(candidates):
                if profile(q).get('frobenius',1024)>1023:continue
                if client.call('route',position=q)['outcome']!='unknown':continue
                queue.append(q)
            queue.sort(key=lambda q:(failures.get(key(q),0),profile(q)['frobenius'],q))
            queues.append(queue)
        requests=[]
        if policy['strategy']=='increasing':
            requests=sorted({p for q in queues for p in q},key=lambda p:(failures.get(key(p),0),profile(p)['frobenius'],p))[:policy['batch_size']]
        else:
            if queues:
                shift=turn%len(queues);queues=queues[shift:]+queues[:shift]
            for depth in range(max(map(len,queues),default=0)):
                for q in queues:
                    if len(q)>depth and q[depth] not in requests:requests.append(q[depth])
                    if len(requests)>=policy['batch_size']:break
                if len(requests)>=policy['batch_size']:break
        if not requests:break
        rows=client.call('exact',positions=requests,seconds=policy['slice_seconds'])['rows']
        # Only the first unfinished request was attempted. Later requests get
        # no timeout penalty; unsupported requests never enter this queue.
        for row in rows:
            if row['outcome']=='unknown':
                k=key(row['position']);failures[k]=failures.get(k,0)+1;break
    for p in sorted(subsidiary,key=lambda p:(-len(p),p)):client.call('close',position=p)
    if client.call('route',position=target)['outcome']!='unknown':
        client.call('submit',proof=client.call('proof',position=target))
