"""Separate public visible bundles from evaluator-only labels and reference proofs."""
from pathlib import Path
from math import gcd

from .common import ROOT, key, read, sha, write
from .episode import execution_profile
from .proof import adapt_graph, adapt_reply, verifier_profile
from .snapshot import export_graph, manifest, snapshot, save_bundle
from sylver.solver import solve_position

TRAINING=((4,5),(4,5,11),(4,6),(6,7))
HELD_OUT=((5,7),(6,7,11),(4,6,9),(8,9))


def tiny_baseline():
    return snapshot([{'position':[2,3],'outcome':'P',
                      'provenance':{'kind':'terminal-no-safe-moves','artifacts':[]},'dependencies':[]}])


def make_bundle(target,base,kind,limits=None,context=''):
    return {'manifest':manifest(target,base,verifier_profile(),execution_profile(limits),kind,context),
            'snapshot':base}


def build_fixtures(output,limits=None,historical=False,live=False):
    out=Path(output);out.mkdir()
    visible=out/'visible';visible.mkdir()
    vault=out/'evaluator';vault.mkdir()
    index={'schema':1,'training':[],'held-out':[],'public-regression':[],'live':[]}
    labels={}
    for kind,targets in (('training',TRAINING),('held-out',HELD_OUT)):
        for p in targets:
            ident=kind+'-'+key(p).replace(',','-')
            bundle=make_bundle(p,tiny_baseline(),kind,limits)
            write(visible/(ident+'.json'),bundle);index[kind].append(ident)
            labels[ident]='P' if p==(4,6) or not solve_position(p).is_winning else 'N'
    if historical:
        paths={'b':ROOT/'sylver/campaigns/targeted-2026-09-22/b-certificate.json',
               'w134':ROOT/'sylver/campaigns/w-seven-2026-09-22/w134-certificate.json',
               'w102':ROOT/'sylver/campaigns/w-six-2026-09-22/w102-certificate.json'}
        for name,path in paths.items():
            cert=read(path);base=tiny_baseline()
            if name=='b':
                h=sha(path.read_bytes());facts=[]
                for k,f in cert['support'].items():
                    if f['evidence']['kind']=='repository-certificate':
                        facts.append({'position':list(map(int,k.split(','))),'outcome':f['outcome'],
                                      'provenance':{'kind':'named-repository-certificate','artifacts':[h]},'dependencies':[]})
                base=snapshot(facts,{h:{'kind':'historical-b-certificate'}})
                proof=adapt_graph(cert,base)
            else:proof=adapt_reply(cert)
            target=list(map(int,proof['root'].split(',')));ident='public-'+name
            write(visible/(ident+'.json'),make_bundle(target,base,'public-regression',limits,
                  'Public solution predates this tournament; regression only, no novel discovery credit.'))
            write(vault/(ident+'-reference.json'),proof)
            labels[ident]=proof['nodes'][proof['root']]['outcome'];index['public-regression'].append(ident)
    if live:
        graph=ROOT/'sylver/campaigns/w-seven-2026-09-22/deep/proof-graph.json'
        base=export_graph(graph,ROOT)
        # One snapshot file also makes frozen input identity easy to inspect.
        # Stored once under visible/knowledge, with content-addressed references.
        for move in (70,86,92,102,108,118):
            kind='public-regression' if move==102 else 'live'
            ident='post-pr5-w-'+str(move)
            context=('W child; W P implies Q N, but U P also requires X N. '
                     'Frozen post-PR5 knowledge. '+('Reply 95 is public in PR13; contaminated regression, not live.' if move==102 else
                     'A public problem; prior exposure may contaminate model comparisons.'))
            save_bundle(visible/(ident+'.json'),make_bundle((16,26,62,98,move),base,kind,limits,context),compact=True)
            index[kind].append(ident)
    write(out/'index.json',index)
    write(vault/'labels.json',labels)
    return index
