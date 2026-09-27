"""Round-robin game leagues: scheduling, ratings, adjudication, and reports.

Every opening is played by every ordered pair of distinct players, so each
pair meets in both seats. Games run in parallel worker processes, and each
finished record is appended to games.jsonl at once, so an interrupted league
keeps every game it completed. Ratings are Bradley-Terry on the Elo scale
over decided games; void games are excluded and listed. Game results are not
proofs: no win, rating, or win rate establishes the outcome of a position.
"""
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import reduce
import math
import os
from pathlib import Path
import platform
import random
import re
import resource
import statistics
import subprocess

from sylver.solver import frobenius_number, solve_position

from .common import ROOT, canonical, sha, write
from .exact import build_tools
from .game import Position
from .players import CACHE, NATIVE, PLAYERS, builtin_command
from .referee import CLOCK, SEATS, own_cgroup, play_game

ENDERS = ((4, 5), (4, 7), (5, 6), (5, 7), (6, 7), (7, 8))
BANDS = ((0, 60), (60, 100), (100, 140), (140, 180))
RESEARCH = (('16', (16,)), ('16-26', (16, 26)), ('W', (16, 26, 62, 98)), ('X', (16, 26, 82, 88)))
SUITES = ('empty', 'enders', 'database', 'research')
ISOLATION = ('**Players are not isolated.** They run as this user without a sandbox, so a player can write '
             "into its opponent's pipes through /proc (making it appear to name 1), signal or trace it, or change "
             'files. Results are meaningful only when every player is a trusted program.')
METHODS = {'cgroup': 'in their own cgroup (cumulative cpu.stat usage of every descendant; cgroup.kill at game end)',
           'session': 'by /proc sums over their session (the fallback without cgroup delegation)'}
BOOTSTRAP = 200


def suite(name, seed=0, per_band=1):
    """Openings {'name','start','outcome','note'}; outcome is 'N' or 'P' for
    the player to move under perfect play, or None when it is unknown."""
    if name == 'empty':
        return [{'name': 'empty', 'start': [], 'outcome': None,
                 'note': 'the real game: uncapped it is N (naming 5 wins, Hutchings); capped play has no known outcome'}]
    if name == 'enders':
        return [{'name': f'ender-{a}-{b}', 'start': [a, b], 'outcome': 'N' if solve_position((a, b)).is_winning else 'P',
                 'note': 'coprime pair; outcome by the Python reference solver'} for a, b in ENDERS]
    if name == 'database':
        rows = CACHE.read_text().splitlines()
        order = list(range(len(rows)))
        random.Random(seed).shuffle(order)
        cells = {(band, o): [] for band in BANDS for o in 'PN'}
        for i in order:
            key, bit = rows[i].split()
            gens = [int(v) for v in key.split(',')]
            if reduce(math.gcd, gens) != 1:
                continue
            f = frobenius_number(gens)
            cell = next((c for (band, o), c in cells.items()
                         if band[0] <= f < band[1] and o == ('P' if bit == '1' else 'N')), None)
            if cell is not None and len(cell) < per_band:
                cell.append((gens, f))
                if all(len(c) == per_band for c in cells.values()):
                    break
        return [{'name': f'db-{band[0]}-{band[1]}-{o}{j}', 'start': gens, 'outcome': o,
                 'note': f'exact cache row; Frobenius number {f}'}
                for (band, o), cell in cells.items() for j, (gens, f) in enumerate(cell)]
    if name == 'research':
        return [{'name': n, 'start': list(s), 'outcome': None, 'note': 'open question; exhibition only'} for n, s in RESEARCH]
    raise ValueError(f'unknown suite {name!r}')


def bradley_terry(results, players, prior=0.5, iterations=5000):
    """MM iterations (Hunter 2004) with `prior` virtual wins and losses
    against a fixed anchor of strength 1, so undefeated or winless players
    get finite ratings. Returned on the Elo scale with mean zero."""
    wins = {p: prior for p in players}; pairs = {}
    for w, l in results:
        wins[w] += 1; k = tuple(sorted((w, l))); pairs[k] = pairs.get(k, 0) + 1
    s = {p: 1.0 for p in players}
    for _ in range(iterations):
        new = {}
        for p in players:
            d = 2 * prior / (s[p] + 1.0)
            for q in players:
                if q != p:
                    n = pairs.get(tuple(sorted((p, q))), 0)
                    if n: d += n / (s[p] + s[q])
            new[p] = wins[p] / d
        done = max(abs(new[p] - s[p]) for p in players) < 1e-12; s = new
        if done: break
    elo = {p: 400 * math.log10(s[p]) for p in players}
    mean = sum(elo.values()) / len(elo)
    return {p: elo[p] - mean for p in players}


def resolve(name, tools, executable=None, seed=0):
    """A player: a built-in by name (exact and book get the native solver
    built in ``tools``) or an external program at an absolute path."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]*', name):
        raise ValueError(f'player name {name!r} must be letters, digits, and _.+-')
    if executable is not None:
        if not Path(executable).is_absolute():
            raise ValueError(f'external player {name} needs an absolute executable path')
        return {'name': name, 'command': [str(executable)]}
    if name not in PLAYERS:
        raise ValueError(f'unknown built-in player {name!r}')
    options = {'binary': str(build_tools(tools))} if name in ('exact', 'book') else {}
    return {'name': name, 'builtin': name, 'options': options, 'command': builtin_command(name, seed, options), 'cwd': str(ROOT)}


def _seat(name, player, seed):
    if 'builtin' in player:
        player = dict(player, command=builtin_command(player['builtin'], seed, player.get('options')))
    return dict(player, name=name)


def _void(game, opening, max_move, clock, detail):
    p = Position(opening['start'], max_move=max_move)
    return {'schema': 1, 'game': game['id'], 'rules': {'max_move': max_move, 'loser': 'names-1'}, 'start': list(p.start),
            'players': {s: {'name': game[s], 'command_sha256': None} for s in SEATS}, 'clock': clock,
            'setup': {s: None for s in SEATS}, 'moves': [],
            'result': {'winner': None, 'loser': None, 'reason': 'void', 'detail': detail},
            'final': {'generators': list(p.generators), 'capped': p.capped(), 'over': p.over()},
            'cpu_totals': {s: 0.0 for s in SEATS}, 'accounting': {s: None for s in SEATS}}


def run_league(players, openings, output, max_move=1000, clock=None, workers=4, seed=0, analyze_bound=0, command=None):
    """Play every opening with every ordered pair of distinct players and
    return the standings. plan.json is written before the first game;
    built-in players (``builtin`` key) are reseeded with seed+i for game i.
    ``command``, if given, is recorded as the way to reproduce the league."""
    output, clock = Path(output), dict(CLOCK, **(clock or {}))
    if len(players) < 2 or len({o['name'] for o in openings}) != len(openings) or type(workers) is not int or workers < 1:
        raise ValueError('a league needs two or more players, uniquely named openings, and a positive worker count')
    for o in openings:
        Position(o['start'], max_move=max_move)
    output.mkdir()
    names, by_name = list(players), {o['name']: o for o in openings}
    schedule = [{'first': a, 'second': b, 'opening': o['name']} for o in openings for a in names for b in names if a != b]
    for i, g in enumerate(schedule):
        g.update(id=f"{i:04d}-{g['opening']}-{g['first']}-vs-{g['second']}", seed=seed + i)
    described = {}
    for n, p in players.items():
        argv = [str(c) for c in p['command']]
        described[n] = {'command': argv, 'command_sha256': sha(argv), 'builtin': p.get('builtin'),
                        'options_sha256': sha(p.get('options', {})) if 'builtin' in p else None}
    plan = {'schema': 1, 'players': described, 'openings': openings, 'rules': {'max_move': max_move, 'loser': 'names-1'},
            'clock': clock, 'seed': seed, 'workers': workers, 'analyze_bound': analyze_bound, 'schedule': schedule,
            'command': command, 'accounting': 'cgroup' if own_cgroup() else 'session', 'host': {'python': platform.python_version(), 'platform': platform.platform(),
                                         'cpus': os.cpu_count()}}
    write(output / 'plan.json', plan)
    (output / 'games').mkdir()
    records, futures, pool = [], {}, ProcessPoolExecutor(workers)
    with (output / 'games.jsonl').open('wb') as log:
        def keep(future):
            g = futures.pop(future)
            try:
                record = future.result()
            except Exception as error:
                record = _void(g, by_name[g['opening']], max_move, clock, f'worker failed: {error!r}')
            log.write(canonical(record) + b'\n')
            log.flush()
            records.append(record)
        try:
            for g in schedule:
                futures[pool.submit(play_game, _seat(g['first'], players[g['first']], g['seed']),
                                    _seat(g['second'], players[g['second']], g['seed']), output / 'games' / g['id'],
                                    by_name[g['opening']]['start'], max_move, clock, g['id'])] = g
            for future in as_completed(list(futures)):
                keep(future)
        except BaseException:
            # Pending games are cancelled; games already running finish during
            # the shutdown and are logged too, so every completed game is kept.
            pool.shutdown(cancel_futures=True)
            for future in [f for f in futures if f.done() and not f.cancelled()]:
                if future.exception() is None or isinstance(future.exception(), Exception):
                    keep(future)
            raise
    pool.shutdown()
    records.sort(key=lambda r: r['game'])
    analysis = (analyze(records, plan, build_tools(output.parent / 'arena-tools'), analyze_bound, workers)
                if analyze_bound else None)
    result = standings(plan, records, analysis)
    write(output / 'standings.json', result)
    (output / 'REPORT.md').write_text(render(plan, records, result))
    return result


def _native(binary, key, seconds=60):
    try:
        out = subprocess.run([str(binary), *key.split(',')], capture_output=True, text=True, timeout=seconds)
    except subprocess.TimeoutExpired:
        return None
    match = NATIVE.fullmatch(out.stdout.strip())
    return match[1] if out.returncode == 0 and match else None


def analyze(records, plan, binary, bound, workers=4):
    """Native exact outcomes (60 s each, unknown on timeout) of every reached
    position with gcd one and Frobenius number at most ``bound`` (and the
    cap, so capped play is exact), before and after each move from one. A
    blunder is a move from an N-position to an N-position. Analysis CPU is
    measured separately and never changes a result."""
    max_move = plan['rules']['max_move']
    bound, games, moves, keys = min(bound, max_move, 1023), {g['id']: g for g in plan['schedule']}, [], {}
    for r in records:
        p = Position(r['start'], max_move=max_move)
        for m in r['moves']:
            q = p.play(m['move'])
            if p.gcd() == 1 and p.frobenius() <= bound:
                moves.append((games[r['game']][m['seat']], p.key(), q.key()))
                keys.update({p.key(): p.frobenius(), q.key(): q.frobenius()})
            p = q
    start = resource.getrusage(resource.RUSAGE_CHILDREN)
    order = sorted(keys, key=lambda k: (keys[k], k))
    with ThreadPoolExecutor(workers) as pool:
        outcome = dict(zip(order, pool.map(lambda k: _native(binary, k), order)))
    end = resource.getrusage(resource.RUSAGE_CHILDREN)
    per = {n: Counter(analysed=0, from_n=0, blunders=0, unknown=0) for n in plan['players']}
    for name, before, after in moves:
        c = per[name]
        c['analysed'] += 1
        if outcome[before] is None:
            c['unknown'] += 1
        elif outcome[before] == 'N':
            c['from_n'] += 1
            if outcome[after] is None:
                c['unknown'] += 1
            elif outcome[after] == 'N':
                c['blunders'] += 1
    return {'bound': bound, 'positions': len(keys), 'unknown_positions': sum(v is None for v in outcome.values()),
            'cpu_seconds': round(end.ru_utime + end.ru_stime - start.ru_utime - start.ru_stime, 3),
            'players': {n: dict(c) for n, c in per.items()}}


def standings(plan, records, analysis=None):
    """Scores, ratings with bootstrap intervals, and the report's tables."""
    names, games = list(plan['players']), {g['id']: g for g in plan['schedule']}
    openings, max_move = {o['name']: o for o in plan['openings']}, plan['rules']['max_move']
    decided = [r for r in records if r['result']['winner']]
    pairs = [(games[r['game']][r['result']['winner']], games[r['game']][r['result']['loser']]) for r in decided]
    elo, rng, samples = bradley_terry(pairs, names), random.Random(plan['seed']), defaultdict(list)
    for _ in range(BOOTSTRAP if pairs else 0):
        for p, v in bradley_terry([rng.choice(pairs) for _ in pairs], names).items():
            samples[p].append(v)
    players, h2h, reasons = {}, {a: {b: 0 for b in names if b != a} for a in names}, {n: Counter() for n in names}
    for w, l in pairs:
        h2h[w][l] += 1
    for r in decided:
        reasons[games[r['game']][r['result']['loser']]][r['result']['reason']] += 1
    for n in names:
        won, lost = sum(w == n for w, _ in pairs), sum(l == n for _, l in pairs)
        cut = statistics.quantiles(samples[n], n=40, method='inclusive') if samples[n] else None
        players[n] = {'games': won + lost, 'wins': won, 'losses': lost, 'score': round(won / (won + lost), 6) if won + lost else None,
                      'elo': round(elo[n], 3), 'interval': [round(cut[0], 3), round(cut[-1], 3)] if cut else None}
    table, verdicts = {}, {n: Counter(should_win=0, won_should_win=0, should_lose=0, won_should_lose=0) for n in names}
    for name, o in openings.items():
        start = Position(o['start'], max_move=max_move)
        known = o['outcome'] if not start.capped() else None
        rows = [r for r in decided if games[r['game']]['opening'] == name]
        should = {'N': 'first', 'P': 'second'}.get(known)
        table[name] = {'start': list(start.start), 'outcome': known, 'capped': start.capped(),
                       'frobenius': start.frobenius(), 'games': len(rows),
                       'first_wins': sum(r['result']['winner'] == 'first' for r in rows),
                       'perfect_winner_wins': sum(r['result']['winner'] == should for r in rows) if should else None}
        for r in rows if should else ():
            for seat in SEATS:
                c, won = verdicts[games[r['game']][seat]], r['result']['winner'] == seat
                c['should_win' if seat == should else 'should_lose'] += 1
                c['won_should_win' if seat == should else 'won_should_lose'] += won
    cpu = {}
    for n in names:
        used = [m['cpu'] for r in records for m in r['moves'] if games[r['game']][m['seat']] == n]
        setup = [r['setup'][s]['cpu'] for r in records for s in SEATS if games[r['game']][s] == n and r['setup'][s]]
        cpu[n] = {'moves': len(used), 'mean': round(statistics.fmean(used), 6) if used else None,
                  'max': max(used, default=None), 'setup_mean': round(statistics.fmean(setup), 6) if setup else None}
    accounting = Counter(m for r in records for m in r['accounting'].values() if m)
    return {'schema': 1, 'games': len(records), 'decided': len(decided), 'accounting': dict(sorted(accounting.items())),
            'void': [{'game': r['game'], 'detail': r['result']['detail'][-300:]} for r in records if not r['result']['winner']],
            'players': players, 'head_to_head': h2h, 'loss_reasons': {n: dict(c) for n, c in reasons.items()},
            'openings': table, 'adjudication': {n: dict(c) for n, c in verdicts.items()}, 'cpu': cpu, 'analysis': analysis}


def _table(header, rows, left=1):
    """A Markdown table; the first ``left`` columns are text, the rest numbers."""
    return ['| ' + ' | '.join(header) + ' |', '| ' + ' | '.join('---' if i < left else '---:' for i in range(len(header))) + ' |',
            *('| ' + ' | '.join(map(str, row)) + ' |' for row in rows)]


def render(plan, games, standings):
    s, clock, cap = standings, plan['clock'], plan['rules']['max_move']
    names = sorted(s['players'], key=lambda n: (-s['players'][n]['elo'], n))
    seats = sum(s['accounting'].values())
    accounting = '; '.join(
        f"{'all' if n == seats else f'{n} of'} {seats} player seats {METHODS[m]}" for m, n in s['accounting'].items()) or 'none'
    openings = {o['name']: s['openings'][o['name']] for o in plan['openings']}   # plan order, even after a JSON round trip
    known = {n: o for n, o in openings.items() if o['outcome']}
    lines = ['# Game arena league', '',
             '**Game results are not proofs.** A win, a rating, or a win rate here is evidence about these '
             'programs under these clocks, never about the outcome of a position. Openings that are *capped* '
             f'(gcd above one, or Frobenius number above the move cap {cap}) follow a house rule: moves are '
             f'limited to 2..{cap}, which never ends a game early but removes larger moves, so their games say '
             'nothing about real Sylver Coinage. Only openings with gcd one and Frobenius number at most the '
             'cap are exact, and only those are adjudicated.', '', ISOLATION, '',
             f"- Players: {', '.join(names)} (commands and digests in `plan.json`).",
             f"- Openings: {len(openings)} ({len(known)} with a known outcome, "
             f"{sum(o['capped'] for o in openings.values())} capped).",
             f'- Rules: name an integer in 2..{cap} outside the semigroup; the player who must name 1 loses.',
             f"- Clock: {clock['cpu_base']} s CPU plus {clock['cpu_increment']} s per legal move; setup up to "
             f"{clock['setup_cpu']} s CPU and {clock['setup_wall']} s wall, not charged; per-move wall limit "
             '3 x remaining CPU + 5 s.',
             f"- CPU accounting: {accounting}.",
             f"- Games: {s['games']} ({s['decided']} decided, {len(s['void'])} void); seed {plan['seed']}; "
             f"{plan['workers']} parallel games.", '', '## Standings', '']
    lines += _table(['Player', 'Games', 'W', 'L', 'Score', 'Elo', '95% interval'], [
        (n, p['games'], p['wins'], p['losses'], '—' if p['score'] is None else f"{100 * p['score']:.1f}%", f"{p['elo']:+.0f}",
         '—' if not p['interval'] else f"[{p['interval'][0]:+.0f}, {p['interval'][1]:+.0f}]")
        for n, p in ((n, s['players'][n]) for n in names)])
    lines += ['', f'Elo is a Bradley–Terry rating (MM, 0.5 virtual wins and losses against a fixed anchor) with '
              f'mean zero; the interval holds the 2.5–97.5 percentiles of {BOOTSTRAP} bootstrap resamples of the '
              'decided games.', '', '## Head to head', '', 'Wins–losses of the row player against the column player, '
              'over both seats and all openings.', '']
    lines += _table(['', *names], [(a, *('—' if a == b else f"{s['head_to_head'][a][b]}–{s['head_to_head'][b][a]}" for b in names))
                                   for a in names])
    reasons = sorted({k for c in s['loss_reasons'].values() for k in c})
    lines += ['', '## Loss reasons', '']
    lines += _table(['Player', *reasons], [(n, *(s['loss_reasons'][n].get(k, 0) for k in reasons)) for n in names])
    lines += ['', '## Openings with a known outcome', '', 'Outcome is for the player to move under perfect play '
              '(N: the first player should win; P: the second). Capped play is exact here. Each outcome comes from '
              "the source in the opening's note in `plan.json`: the Python reference solver for enders, the frozen "
              'exact cache for database openings.', '']
    lines += _table(['Opening', 'Start', 'Outcome', 'Frobenius', 'Perfect-play winner won'], [
        (n, '{' + ','.join(map(str, o['start'])) + '}', o['outcome'], o['frobenius'], f"{o['perfect_winner_wins']}/{o['games']}")
        for n, o in known.items()], left=3)
    lines += ['']
    lines += _table(['Player', 'Won when it should win', 'Won when it should lose'], [
        (n, f"{c['won_should_win']}/{c['should_win']}", f"{c['won_should_lose']}/{c['should_lose']}")
        for n, c in ((n, s['adjudication'][n]) for n in names)])
    other = {n: o for n, o in openings.items() if not o['outcome']}
    if other:
        lines += ['', '## Openings without adjudication', '', 'Capped or of unknown outcome: these results measure '
                  'the programs, not the position.', '']
        lines += _table(['Opening', 'Start', 'Capped', 'Games', 'First player won'], [
            (n, '{' + ','.join(map(str, o['start'])) + '}', 'yes' if o['capped'] else 'no', o['games'], o['first_wins'])
            for n, o in other.items()], left=3)
    lines += ['', '## CPU per move', '']
    lines += _table(['Player', 'Moves', 'Mean CPU (s)', 'Max CPU (s)', 'Mean setup CPU (s)'], [
        (n, c['moves'], '—' if c['mean'] is None else f"{c['mean']:.3f}", '—' if c['max'] is None else f"{c['max']:.3f}",
         '—' if c['setup_mean'] is None else f"{c['setup_mean']:.3f}") for n, c in ((n, s['cpu'][n]) for n in names)])
    if s['accounting'].get('session'):
        lines += ['', 'CPU from /proc has clock-tick resolution (typically 10 ms), so very fast moves read as 0.']
    a = s['analysis']
    if a:
        lines += ['', f"## Blunders (exact analysis, Frobenius number at most {a['bound']})", '',
                  'A blunder is a move from an N-position to an N-position. Positions were solved by the native '
                  f"solver, 60 s each: {a['positions']} positions, {a['unknown_positions']} unknown after the limit. "
                  f"Analysis CPU was {a['cpu_seconds']:.1f} s; it never affects results.", '']
        lines += _table(['Player', 'Analysed moves', 'From N', 'Blunders', 'Blunder rate', 'Unknown'], [
            (n, c['analysed'], c['from_n'], c['blunders'], f"{100 * c['blunders'] / c['from_n']:.1f}%" if c['from_n'] else '—',
             c['unknown']) for n, c in ((n, a['players'][n]) for n in names)])
    lines += ['', '## Void games', '']
    lines += [f"- `{v['game']}`: {v['detail'].splitlines()[-1] if v['detail'] else 'no detail'}" for v in s['void']] or ['None.']
    lines += ['', '## Limitations', '']
    if s['accounting'].get('cgroup'):
        lines += ['- A same-user process can move itself out of its cgroup and so escape both the clock and the '
                  'kill at game end.']
    if s['accounting'].get('session'):
        lines += ['- Under /proc session sums, CPU of children that no session member reaps (SIGCHLD ignored, '
                  'double-fork orphans reaped by init) is not charged, and a process that leaves its session is '
                  'neither charged nor killed.']
    lines += [
              '- Players run as the same user without a sandbox; see the warning at the top.',
              '- CPU timings depend on the machine and its load, and the exact players stop searching when their '
              'budget ends, so a rerun need not reproduce every game.', '', '## Reproduce', '']
    lines += (['```sh', plan['command'], '```'] if plan.get('command') else
              ['Rerun `run_league` with the players, openings, rules, clock, and seed recorded in `plan.json`.'])
    return '\n'.join(lines) + '\n'
