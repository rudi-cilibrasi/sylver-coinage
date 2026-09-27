"""Bounded declarative policy programs; no competitor eval/import/file access."""
import random
from .common import canonical, fields, key, position, profile

BASELINES={
    'increasing':{'strategy':'increasing','batch_size':1,'odd_limit':65,'slice_seconds':.3,'rounds':12,'subsidiary_depth':0,'proof_style':'compact'},
    'interleaved':{'strategy':'interleaved','batch_size':8,'odd_limit':65,'slice_seconds':.6,'rounds':12,'subsidiary_depth':0,'proof_style':'compact'},
    'routes-short':{'strategy':'routes-short','batch_size':8,'odd_limit':65,'slice_seconds':.6,'rounds':12,'subsidiary_depth':2,'proof_style':'compact'},
}
# Certificate golf (public database targets): certify cheaply using hints.
GOLF={
    'golf-root':{'strategy':'golf-root','batch_size':1,'odd_limit':301,'slice_seconds':60,'rounds':1,'subsidiary_depth':0,'proof_style':'compact'},
    'golf-witness':{'strategy':'golf-witness','batch_size':1,'odd_limit':301,'slice_seconds':60,'rounds':1,'subsidiary_depth':0,'proof_style':'compact'},
    'golf-probe':{'strategy':'golf-probe','batch_size':3,'odd_limit':301,'slice_seconds':120,'rounds':1,'subsidiary_depth':0,'proof_style':'compact'},
    # Hint-free control: learns what hints would have said by exact search.
    'golf-blind':{'strategy':'golf-blind','batch_size':1,'odd_limit':301,'slice_seconds':300,'rounds':3,'subsidiary_depth':0,'proof_style':'compact'},
}
PROMPTS={
    'default':'Use exact routing first. Submit only supported proofs. Unknown is not P.',
    'short-first':'Inspect complete short covers before spending on finite witness searches.',
    'compact':'Prefer a small proof, while accounting for its full fresh verification cost.',
}


def validate_policy(policy):
    fields(policy,('strategy','batch_size','odd_limit','slice_seconds','rounds','subsidiary_depth','proof_style'))
    if policy['strategy'] not in ('increasing','interleaved','routes-short','golf-root','golf-witness','golf-probe','golf-blind'):
        raise ValueError('unsupported policy program')
    for name,lo,hi in (('batch_size',1,128),('odd_limit',3,1023),('rounds',1,1000),('subsidiary_depth',0,3)):
        if type(policy[name]) is not int or not lo<=policy[name]<=hi:raise ValueError('policy limit outside profile')
    if type(policy['slice_seconds']) not in (int,float) or not 0<policy['slice_seconds']<=300:raise ValueError('invalid slice')
    if policy['proof_style'] not in ('compact','witness'):raise ValueError('invalid proof style')
    return policy


def _genus(p):
    """Number of gaps: the size of the finite game's move set, a cost proxy."""
    from sylver.solver import FiniteSolver
    return len(FiniteSolver(p).gaps())


def run_golf(client,policy):
    """Certify a golf target cheaply; hints steer, the fixed verifier decides.

    golf-root submits one finite leaf. golf-witness answers an N target with
    the hinted finite P child of fewest gaps. golf-probe, when there is a
    choice, races bounded exact queries over up to batch_size such children
    and the root, each capped by the time that could still beat the best
    estimate (C+100)*(seconds+1), and submits the cheapest; probing is
    charged. golf-blind ignores hints: it computes a finite target's outcome
    exactly, and searches up to `rounds` odd replies for a gcd-two target's
    witness. Finite P targets get a root leaf; gcd-two P targets need covers,
    which these strategies do not build.
    """
    target=tuple(client.call('inspect')['manifest']['target']);root=key(target)
    info=client.call('profile',position=target);finite=info['gcd']==1
    if finite and info['frobenius']>1023:return  # beyond the fixed verifier
    blind=policy['strategy']=='golf-blind'
    outcome='unknown' if blind else client.call('hint',positions=[target])['rows'][0]['outcome']
    if outcome=='unknown' and finite:
        outcome=client.call('exact',positions=[target],seconds=policy['slice_seconds'])['rows'][0]['outcome']
    if not finite and blind:outcome='N'  # only N can be certified without a cover
    if outcome=='unknown' or outcome=='P' and not finite:return
    leaf={'schema':1,'root':root,'nodes':{root:{'rule':'finite','outcome':outcome}}}
    if finite and (policy['strategy'] in ('golf-root','golf-blind') or outcome=='P'):
        client.call('submit',proof=leaf);return
    moves=list(info['moves'])
    if info['gcd']==2:moves+=[m for m in range(3,policy['odd_limit']+1,2) if m not in moves]
    candidates=[(m,position((*target,m))) for m in moves]
    candidates=[(m,c) for m,c in candidates if profile(c).get('frobenius',1024)<=1023]
    def edge(m,c):
        return {'schema':1,'root':root,'nodes':{root:{'rule':'edge','outcome':'N','move':m,'child':key(c)},
                                               key(c):{'rule':'finite','outcome':'P'}}}
    if blind:  # gcd-two target: search the cheapest-looking finite replies exactly
        for _,_,m,c in sorted((profile(c)['frobenius'],m,m,c) for m,c in candidates)[:policy['rounds']]:
            if client.call('exact',positions=[c],seconds=policy['slice_seconds'])['rows'][0]['outcome']=='P':
                client.call('submit',proof=edge(m,c));return
        return
    rows=client.call('hint',positions=[c for _,c in candidates])['rows'] if candidates else []
    witnesses=sorted((_genus(c),profile(c)['frobenius'],m,c) for (m,c),r in zip(candidates,rows) if r['outcome']=='P')
    if not witnesses:
        if finite:client.call('submit',proof=leaf)
        return
    options=[(edge(m,c),c,'P') for _,_,m,c in witnesses[:policy['batch_size']]]+([(leaf,target,'N')] if finite else [])
    if policy['strategy']!='golf-probe' or len(options)==1:
        client.call('submit',proof=options[0][0]);return
    best=None;refuted=set()  # best: (estimate, proof)
    for index,(proof,measured,expected) in enumerate(options):
        size=len(canonical(proof))+100
        cap=policy['slice_seconds'] if best is None else min(policy['slice_seconds'],best[0]/size-1)
        if cap<=0:continue
        result=client.call('exact',positions=[measured],seconds=cap)
        found=result['rows'][0]['outcome']
        if found==expected:
            estimate=size*(result['wall_seconds']+1)
            if best is None or estimate<best[0]:best=(estimate,proof)
        elif found!='unknown':refuted.add(index)  # a wrong hint
    fallback=[proof for i,(proof,_,_) in enumerate(options) if i not in refuted]
    if best or fallback:client.call('submit',proof=best[1] if best else fallback[0])


def run_policy(client,policy,seed=0):
    validate_policy(policy)
    random.Random(seed)  # Pin seed even for these deterministic baselines.
    if policy['strategy'].startswith('golf-'):return run_golf(client,policy)
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
