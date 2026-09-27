"""Run with python -m sylver.arena --help."""
import argparse
import json
from pathlib import Path
import sys

from .common import ROOT, canonical, read, write
from .episode import DEFAULT_LIMITS, run_episode
from .evolution import run_evolution
from .exact import build_tools
from .fixtures import build_fixtures
from .pilot import pilot
from .policies import BASELINES, GOLF
from .protocol import Session
from .snapshot import export_graph, validate_bundle, load_bundle
from .tournament import leaderboard, render, reverify, run_tournament


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('fixtures');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--historical',action='store_true');p.add_argument('--live',action='store_true')
    p.add_argument('--cpu-seconds',type=float,default=5.);p.add_argument('--wall-seconds',type=float,default=15.)
    p.add_argument('--memory-mb',type=int,default=512)
    p.add_argument('--model-id',default='none');p.add_argument('--model-requests',type=int,default=0)
    p.add_argument('--model-tokens',type=int,default=0);p.add_argument('--model-cost',type=float,default=0.)
    p.add_argument('--golf',action='store_true',help='certificate-golf panel with pinned database hints')
    p.add_argument('--tiers',default='A,B',help='golf tiers: A,B (finite panel) and C (research, 16 GiB)')
    p=commands.add_parser('inspect');p.add_argument('bundle',type=Path)
    p=commands.add_parser('snapshot');p.add_argument('--graph',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p=commands.add_parser('run');p.add_argument('bundle',type=Path);p.add_argument('--policy',choices=[*BASELINES,*GOLF],default='increasing')
    p.add_argument('--agent',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--tools',type=Path,default=Path('/tmp/sylver-arena-tools'))
    p.add_argument('--seed',type=int,default=0)
    p=commands.add_parser('verify');p.add_argument('episode',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--tools',type=Path,default=Path('/tmp/sylver-arena-tools'))
    p=commands.add_parser('tournament');p.add_argument('bundles',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=int,default=3);p.add_argument('--seed',type=int,default=0)
    p.add_argument('--workers',type=int,default=1,help='concurrent episodes (each separately accounted)')
    p=commands.add_parser('golf-pilot');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--tiers',default='A,B');p.add_argument('--repeats',type=int,default=3)
    p.add_argument('--research-repeats',type=int,default=1);p.add_argument('--workers',type=int,default=1)
    p.add_argument('--seed',type=int,default=0)
    p=commands.add_parser('book');p.add_argument('action',choices=('add','verify','render'))
    p.add_argument('episodes',type=Path,nargs='*');p.add_argument('--book',type=Path,default=ROOT/'sylver/arena/book')
    p.add_argument('--competitor');p.add_argument('--tools',type=Path,default=Path('/tmp/sylver-arena-tools'))
    p=commands.add_parser('report');p.add_argument('tournament',type=Path)
    p=commands.add_parser('pilot');p.add_argument('--output',type=Path,required=True);p.add_argument('--repeats',type=int,default=3);p.add_argument('--seed',type=int,default=0)
    p=commands.add_parser('evolve');p.add_argument('bundles',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--proposer',type=Path);p.add_argument('--agent-template',type=Path);p.add_argument('--candidates',type=int,default=9)
    p.add_argument('--cpu-budget',type=float,default=120.);p.add_argument('--model-requests',type=int,default=0)
    p.add_argument('--model-tokens',type=int,default=0);p.add_argument('--model-cost',type=float,default=0.)
    p=commands.add_parser('verify-proof');p.add_argument('bundle',type=Path);p.add_argument('certificate',type=Path);p.add_argument('--output',type=Path,required=True)
    p=commands.add_parser('resume');p.add_argument('episode',type=Path)
    p=commands.add_parser('admit');p.add_argument('episode',type=Path);p.add_argument('--output',type=Path,required=True)
    p=commands.add_parser('serve');p.add_argument('bundle',type=Path);p.add_argument('--output',type=Path,required=True)
    p=commands.add_parser('_serve_worker',help=argparse.SUPPRESS);p.add_argument('bundle',type=Path);p.add_argument('output',type=Path);p.add_argument('binary',type=Path);p.add_argument('hints',nargs='?')
    trusted=('Players run as this user without a sandbox and can interfere with each other (for example, '
             "write into the opponent's pipes through /proc); run only trusted programs. Game results are not proofs.")
    for name in ('play','league'):
        p=commands.add_parser(name,description=trusted,help=f'{name} Sylver Coinage games between trusted programs')
        if name=='play':
            p.add_argument('first');p.add_argument('second');p.add_argument('--start',default='');p.add_argument('--games',type=int,default=2)
        else:
            p.add_argument('--players',default='random,smallest,exact,book');p.add_argument('--suites',default='empty,enders,database')
            p.add_argument('--external',action='append',default=[],metavar='NAME=/abs/executable')
            p.add_argument('--per-band',type=int,default=1);p.add_argument('--workers',type=int,default=4)
            p.add_argument('--analyze-bound',type=int,default=0)
        p.add_argument('--output',type=Path,required=True);p.add_argument('--max-move',type=int,default=1000)
        p.add_argument('--cpu',type=float,default=2.);p.add_argument('--increment',type=float,default=.1);p.add_argument('--seed',type=int,default=0)
    args=parser.parse_args()
    if args.command=='fixtures' and args.golf:
        from .golf import build_golf
        print(json.dumps(build_golf(args.output,tuple(args.tiers.split(','))),indent=2))
    elif args.command=='fixtures':print(json.dumps(build_fixtures(args.output,dict(DEFAULT_LIMITS,cpu_seconds=args.cpu_seconds,wall_seconds=args.wall_seconds,memory_mb=args.memory_mb,model_id=args.model_id,model_requests=args.model_requests,model_tokens=args.model_tokens,model_cost=args.model_cost),historical=args.historical,live=args.live),indent=2))
    elif args.command=='inspect':
        bundle=load_bundle(args.bundle);validate_bundle(bundle);print(json.dumps(bundle['manifest'],indent=2))
    elif args.command=='snapshot':
        if args.output.exists():raise ValueError('output already exists')
        write(args.output,export_graph(args.graph,ROOT));print(args.output)
    elif args.command=='run':
        from .golf import bundle_hints
        bundle=load_bundle(args.bundle)
        r=run_episode(bundle,{**BASELINES,**GOLF}[args.policy],args.output,args.tools,args.seed,
                      agent=read(args.agent) if args.agent else None,hints=bundle_hints(args.bundle,bundle))
        print(json.dumps({k:r[k] for k in ('status','C','T','S','log_score')},indent=2))
    elif args.command=='verify':print(json.dumps(reverify(args.episode,args.output,args.tools),indent=2))
    elif args.command=='tournament':
        from .common import sha
        from .golf import bundle_hints, competitors
        bundles=[load_bundle(p) for p in args.bundles]
        golf=all(b['manifest']['kind']=='golf' for b in bundles)
        if any(b['manifest']['kind']=='golf' for b in bundles) and not golf:raise ValueError('do not mix golf and search tasks')
        run_tournament(bundles,competitors() if golf else {n:{'policy':p} for n,p in BASELINES.items()},
                       args.output,args.output.parent/'arena-tools',args.repeats,args.seed,
                       hints={sha(b['manifest']):bundle_hints(p,b) for p,b in zip(args.bundles,bundles)},
                       workers=args.workers)
        print(args.output/'REPORT.md')
    elif args.command=='golf-pilot':
        from .golf import golf_pilot
        print(golf_pilot(args.output,tuple(args.tiers.split(',')),args.repeats,args.seed,args.workers,args.research_repeats))
    elif args.command=='book':
        from .book import add_certificate, render_book, verify_book
        if args.action=='add':
            for episode in args.episodes:
                print(json.dumps(add_certificate(args.book,episode,args.tools,args.competitor),indent=2))
            (args.book/'BOOK.md').write_text(render_book(args.book))
        elif args.action=='verify':
            report=verify_book(args.book,args.tools);print(json.dumps(report,indent=2))
            if not all(r['ok'] for r in report):raise SystemExit(1)
        else:(args.book/'BOOK.md').write_text(render_book(args.book));print(args.book/'BOOK.md')
    elif args.command=='report':
        entries=[(r['competitor'],read(args.tournament/r['directory']/'receipt.json')) for r in read(args.tournament/'runs.json')]
        print(render(entries))
    elif args.command=='pilot':pilot(args.output,args.repeats,args.seed);print(args.output/'REPORT.md')
    elif args.command=='evolve':
        run_evolution([load_bundle(p) for p in args.bundles],args.output,args.output.parent/'arena-tools',
                      max_candidates=args.candidates,cpu_budget=args.cpu_budget,model_requests=args.model_requests,
                      model_tokens=args.model_tokens,model_cost=args.model_cost,
                      proposer=read(args.proposer) if args.proposer else None,
                      agent_template=read(args.agent_template) if args.agent_template else None)
        print(args.output/'result.json')
    elif args.command=='verify-proof':
        from .tournament import verify_submission
        result=verify_submission(load_bundle(args.bundle),read(args.certificate),args.output,args.output.parent/'arena-tools')
        print(json.dumps(result,indent=2))
        if not result['valid']:raise SystemExit(1)
    elif args.command=='resume':
        from .episode import resume_episode
        print(json.dumps(resume_episode(args.episode),indent=2))
    elif args.command=='admit':
        from .tournament import admit
        print(admit(args.episode,args.output,args.output.parent/'arena-tools'))
    elif args.command=='serve':
        import subprocess,time
        args.output=args.output.resolve();args.output.mkdir()
        bundle=load_bundle(args.bundle);write(args.output/'bundle.json',bundle)
        binary=build_tools(args.output/'tools')
        work=args.output/'work';work.mkdir()
        control=args.output/'supervisor.json'
        from .golf import bundle_hints
        hints=bundle_hints(args.bundle,bundle)  # the copied bundle's directory has no hints/
        write(control,{'command':[sys.executable,'-m','sylver.arena','_serve_worker',
                                 str(args.output/'bundle.json'),str(work),str(binary),*([hints] if hints else [])],
                       'output':str(args.output/'accounting'),
                       'limits':bundle['manifest']['execution']['limits'],'cwd':str(ROOT)})
        process=subprocess.Popen([sys.executable,'-m','sylver.arena.supervisor',str(control)],cwd=ROOT)
        stream=args.output/'accounting/stdout.txt';offset=0
        def forward():
            nonlocal offset
            if stream.exists():
                with stream.open('rb') as f:f.seek(offset);chunk=f.read();offset+=len(chunk)
                if chunk:sys.stdout.buffer.write(chunk);sys.stdout.buffer.flush()
        try:
            while process.poll() is None:forward();time.sleep(.01)
            forward()
        finally:
            if process.poll() is None:process.terminate();process.wait()
        # Interactive exploration has accountable CPU, but no discovery+proof
        # score. Rated programs use run --agent and independent verification.
    elif args.command=='play':
        # Game 0: FIRST moves first; seats alternate. Names containing / are external absolute executables.
        from .league import resolve
        from .referee import game_clock, play_game
        clock=game_clock({'cpu_base':args.cpu,'cpu_increment':args.increment})
        start=[int(v) for v in args.start.split(',') if v];args.output.mkdir()
        seat=lambda spec,seed:resolve(Path(spec).name if '/' in spec else spec,args.output.parent/'arena-tools',spec if '/' in spec else None,seed)
        for i in range(args.games):
            first,second=(args.first,args.second)[::1 if i%2==0 else -1]
            r=play_game(seat(first,args.seed+i),seat(second,args.seed+i),args.output/f'game-{i:02d}',start,args.max_move,clock,f'game-{i:02d}')
            names={'first':r['players']['first']['name'],'second':r['players']['second']['name']}
            print(json.dumps({'game':r['game'],**names,'winner':names.get(r['result']['winner']),
                              'reason':r['result']['reason'],'plies':len(r['moves'])}),flush=True)
    elif args.command=='league':
        import shlex
        from .league import resolve, run_league, suite
        from .referee import game_clock
        tools=args.output.parent/'arena-tools';players={n:resolve(n,tools) for n in args.players.split(',') if n}
        for item in args.external:
            name,_,path=item.partition('=')
            if name in players:raise SystemExit(f'duplicate player {name}')
            players[name]=resolve(name,tools,path)
        openings=[o for s in args.suites.split(',') if s for o in suite(s,args.seed,args.per_band)]
        run_league(players,openings,args.output,args.max_move,game_clock({'cpu_base':args.cpu,'cpu_increment':args.increment}),
                   args.workers,args.seed,args.analyze_bound,command='python -m sylver.arena '+shlex.join(sys.argv[1:]))
        print(args.output/'REPORT.md')
    elif args.command=='_serve_worker':
        from .common import decode
        bundle=load_bundle(args.bundle)
        session=Session(bundle,args.binary,args.output,bundle['manifest']['execution']['limits'],hints=args.hints)
        for line in sys.stdin:
            print(json.dumps(session.request(decode(line))),flush=True)


if __name__=='__main__':main()
