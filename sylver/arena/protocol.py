"""Version-1 local search protocol shared by policies and agent adapters."""
import json
import math
from pathlib import Path
import time

from .common import canonical, fields, from_key, key, legal, position, profile, sha, write
from .exact import batch
from .proof import canonical_proof
from .snapshot import validate_bundle


def membership(p,bound):
    bits=1;mask=(1<<(bound+1))-1
    for g in p:
        shift=g
        while shift<=bound:
            bits|=(bits<<shift)&mask;shift*=2
    return bits


class Session:
    def __init__(self,bundle,binary,output,limits,proof_style='compact',resume_nodes=None):
        validate_bundle(bundle)
        self.bundle=json.loads(canonical(bundle));self.binary=binary;self.output=Path(output)
        self.output.mkdir(exist_ok=True)
        self.limits=limits;self.started=time.monotonic();self.queries=0;self.calls=0
        self.proof_style=proof_style;self.submitted=False
        self.nodes={key(f['position']):{'rule':'baseline','outcome':f['outcome'],'fact':ident}
                    for ident,f in bundle['snapshot']['facts'].items()}
        if resume_nodes:
            for k,n in resume_nodes.items():
                if k in self.nodes and self.nodes[k]['outcome']!=n['outcome']:raise ValueError('conflicting episode checkpoint')
                self.nodes.setdefault(k,n)
        self.p_index=[];self.indexed=set()
        self.transcript=self.output/'transcript.jsonl'

    def route(self,p):
        p=position(p);k=key(p)
        if k in self.nodes:return self.nodes[k]
        for q,n in list(self.nodes.items()):
            if n['outcome']=='P' and q not in self.indexed:
                qs=from_key(q);self.p_index.append((q,qs,sum(1<<x for x in qs)))
                self.indexed.add(q)
        bound=max([max(p),*(max(q) for _,q,_ in self.p_index)],default=max(p))
        sbits=membership(p,bound);sgens=sum(1<<x for x in p)
        for q,qs,qgens in self.p_index:
            if sgens & ~membership(qs,bound):continue
            missing=qgens & ~sbits
            if missing.bit_count()==1:
                move=missing.bit_length()-1
                if legal(p,move) and key((*p,move))==q:
                    self.nodes[k]={'rule':'edge','outcome':'N','move':move,'child':q}
                    return self.nodes[k]
        return None

    def close(self,p):
        p=position(p);k=key(p)
        if self.route(p):return self.nodes[k]
        info=profile(p)
        rows=[]
        for move in info['moves']:
            child=key((*p,move));n=self.route(from_key(child))
            if n and n['outcome']=='P':
                self.nodes[k]={'rule':'edge','outcome':'N','move':move,'child':child}
                return self.nodes[k]
            if not n or n['outcome']!='N':return None
            rows.append({'move':move,'child':child})
        if info['complete']:
            self.nodes[k]={'rule':'cover','outcome':'P','tail':info['tail'],'children':rows}
            return self.nodes[k]
        return None

    def proof(self,p):
        k=key(p);nodes={}
        def visit(k):
            if k in nodes:return
            if k not in self.nodes:raise ValueError('unknown proof dependency')
            n=self.nodes[k];nodes[k]=n
            if n['rule']=='edge':visit(n['child'])
            if n['rule']=='cover':
                for row in n['children']:visit(row['child'])
        visit(k)
        return {'schema':1,'root':k,'nodes':nodes}

    def request(self,request):
        self.calls+=1
        if self.calls>self.limits.get('protocol_calls',10000):raise ValueError('protocol call limit')
        fields(request,('id','op','args'))
        op,args=request['op'],request['args']
        try:result=self.dispatch(op,args)
        except (ValueError,KeyError,TypeError,OverflowError) as exc:
            result={'status':'error','error':str(exc)}
        response={'schema':1,'id':request['id'],'result':result}
        with self.transcript.open('ab') as f:
            f.write(canonical({'request':request,'response':response})+b'\n');f.flush()
        write(self.output/'known-nodes.json',{k:n for k,n in self.nodes.items() if n['rule']!='baseline'})
        return response

    def dispatch(self,op,args):
        if op=='inspect':
            fields(args,())
            return {'manifest':self.bundle['manifest'],'profile':profile(self.bundle['manifest']['target'])}
        if op=='budget':
            fields(args,())
            return {'limits':self.limits,'wall_elapsed':time.monotonic()-self.started,
                    'queries':self.queries,'calls':self.calls,
                    'cpu_enforcement':'aggregate supervisor; no free restarts'}
        if op in ('lookup','profile','route','close','proof'):
            fields(args,('position',));p=position(args['position']);k=key(p)
            if op=='profile':return profile(p)
            if op=='proof':return self.proof(p)
            n=self.nodes.get(k) if op=='lookup' else self.route(p) if op=='route' else self.close(p)
            return {'position':list(p),'outcome':n['outcome'] if n else 'unknown','node':n}
        if op=='exact':
            fields(args,('positions','seconds'))
            seconds=args['seconds']
            if isinstance(seconds,bool) or not math.isfinite(seconds) or seconds<=0:raise ValueError('invalid query lifetime')
            if not isinstance(args['positions'],list) or not 1<=len(args['positions'])<=128:raise ValueError('invalid batch size')
            ps=[position(p) for p in args['positions']]
            eligible=[p for p in ps if profile(p).get('frobenius',1024)<=1023]
            self.queries+=1
            rows=batch(self.binary,eligible,self.output/f'query-{self.queries:04d}',
                       min(seconds,self.limits['query_wall_seconds'])) if eligible else []
            for row in rows:
                p=tuple(row['position']);k=key(p)
                n={'rule':'finite','outcome':row['outcome']}
                if row['winning_move'] is not None:
                    dest=key((*p,row['winning_move']))
                    self.nodes.setdefault(dest,{'rule':'finite','outcome':'P'})
                    if self.proof_style=='witness':n={'rule':'edge','outcome':'N','move':row['winning_move'],'child':dest}
                old=self.nodes.get(k)
                if old and old['outcome']!=n['outcome']:raise ValueError('contradictory exact result')
                self.nodes.setdefault(k,n)
            completed={key(r['position']):r for r in rows}
            return {'rows':[completed.get(key(p),{'position':list(p),'outcome':'unknown'}) for p in ps]}
        if op=='submit':
            fields(args,('proof',))
            encoded=canonical_proof(args['proof'],self.bundle['snapshot'],self.bundle['manifest']['target'])
            # Structural acceptance is not a win. Only the separate fresh
            # verification stage can set valid=True and award a finite score.
            (self.output/'submission.json').write_bytes(encoded+b'\n')
            self.submitted=True
            return {'status':'awaiting-independent-replay','canonical_bytes':len(encoded)}
        raise ValueError('unknown protocol operation')


class Client:
    def __init__(self,session):self.session=session;self.serial=0
    def call(self,op,**args):
        self.serial+=1
        result=self.session.request({'id':self.serial,'op':op,'args':args})['result']
        if result.get('status')=='error':raise ValueError(result['error'])
        return result
