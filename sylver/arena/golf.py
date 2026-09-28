"""Certificate golf: certify public database results with short, cheap proofs.

The frozen database is an untrusted hint oracle pinned by each golf manifest;
the trusted snapshot is empty, so a certificate's every byte counts in C and
every finite leaf is replayed by the fixed verifier. Golf measures
certification efficiency, not discovery: every target's outcome is public.
"""
from collections import defaultdict
from pathlib import Path
from statistics import median

from .common import ROOT, key, read, sha, write
from .episode import DEFAULT_LIMITS, execution_profile
from .hints import encode, path_for, save
from .proof import verifier_profile
from .snapshot import export_graph, manifest, snapshot

# The post-PR13 evidence graph plus the 305,011-row cache it pins (308,322
# facts). Frozen: the hint digest in every golf manifest pins these bytes.
HINT_GRAPH = 'sylver/campaigns/w-six-2026-09-22/evidence/proof-graph.json'

# Predeclared panel: seeded draws (random.Random(20260927)) from the hint
# database by Frobenius band, accepted by the deterministic native
# root-search state count (tier A at most 2M states; tier B 0.5M-8M) so that
# proof structure, not process start-up, dominates. N targets are drawn among
# N positions with at least one hinted P child: the database records
# outcomes, not winning moves, and a first random draw found hinted P
# children for only 3 of 8 N targets. P targets are root-leaf controls.
# (tier, target, public outcome, root-search states)
GOLF_PANEL = (
    ('A', '16,26,34,38,40,117,123,125,127,131', 'N', 688662),
    ('A', '16,26,30,36,38,40,44,113,121,123,127,131', 'N', 370334),
    ('A', '16,26,30,36,38,50,115,125,139,159', 'N', 759),
    ('A', '16,26,30,38,109,123,127,137', 'P', 1876804),
    ('A', '16,26,28,30,38,79', 'P', 448489),
    ('A', '16,20,26,28,38,111,121,129,135', 'P', 169082),
    ('B', '16,26,36,38,44,56,66,119,137,139,141,147', 'N', 2358078),
    ('B', '16,26,70,82,83,88,133,137', 'N', 1381848),
    ('B', '16,26,82,86,88,93,129,149,163,169', 'N', 3747484),
    ('B', '16,26,38,44,46,56,111,129,131,133', 'P', 3330318),
    ('B', '16,26,34,38,40,115,151,159', 'P', 1390816),
    ('B', '16,26,38,44,50,113,141,147,149,159', 'P', 4797858),
)
# The campaign's own branch refutations around W={16,26,62,98}: moves 134
# (PR #5) and 102 (PR #13) have gcd two, so only a witness can certify them;
# the finite pair after 102 and 89 is a genuine golf choice (root search
# 6,382,154 states, witness 33 child 1,721,485). States: the certificate's
# finite leaf for witness-only targets, the root search otherwise.
GOLF_RESEARCH = (
    ('C', '16,26,62,98,134', 'N', 37192385),
    ('C', '16,26,62,98,102', 'N', 44985582),
    ('C', '16,26,62,89,98,102', 'N', 6382154),
    ('C', '16,26,33,62,89,102', 'P', 1721485),
)
# W={16,26,62,98} has 52 Quiet End obligations, all covered: W is P
# (campaigns/w-p-2026-09-27). Each move m is refuted by a recorded reply. For
# the 43 moves below the refutation is a finite certificate: even moves (gcd
# two) by an odd witness reaching a finite P position, odd moves by a finite
# N position itself (the verifier finds its winning move). Witnesses: the
# campaign graph, the plan2 release certificate, and the September 27 scans.
W = (16, 26, 62, 98)
W_WITNESSED = {2: 3, 18: 5, 19: 23, 22: 15, 27: 19, 28: 25, 30: 111, 34: 39, 38: 55, 40: 11, 44: 19, 46: 17,
               50: 29, 54: 33, 56: 97, 60: 27, 66: 263, 67: 31, 70: 169, 72: 107, 76: 43, 82: 27, 86: 129, 92: 139,
               102: 95, 108: 213, 118: 167, 134: 85}
W_FINITE = (3, 5, 7, 9, 11, 15, 17, 23, 25, 33, 35, 41, 43, 51, 59)
# The other 9 moves were routed through infinite P positions, whose own
# certificates are campaign or published results outside this proof set;
# The Book has finite certificates for all but 12 and 36 (see W.md).
W_INFINITE = {4: (6, '{4,6}'), 6: (4, '{4,6}'), 8: (20, 'G={8,20,26}'), 10: (24, 'K={10,16,24}'),
              12: (14, '{12,14,16}'), 14: (12, '{12,14,16}'), 20: (8, 'G={8,20,26}'),
              24: (10, 'K={10,16,24}'), 36: (56, 'V={16,26,36,56}')}
W_OPEN = ()  # moves with no recorded refutation
W_LIMITS = dict(DEFAULT_LIMITS, cpu_seconds=3600., wall_seconds=7200., memory_mb=16384, query_wall_seconds=3600.)


def w_targets():
    """Golf rows for W's finitely certifiable obligations, move order."""
    from .common import position
    rows = []
    for m in sorted([*W_WITNESSED, *W_FINITE]):
        rows.append(('W', key(position((*W, m))), 'N', None))
    return rows


TIER_LIMITS = {
    'A': dict(DEFAULT_LIMITS, cpu_seconds=600., wall_seconds=1800., memory_mb=8192, query_wall_seconds=600.),
    'B': dict(DEFAULT_LIMITS, cpu_seconds=600., wall_seconds=1800., memory_mb=8192, query_wall_seconds=600.),
    'C': dict(DEFAULT_LIMITS, cpu_seconds=3600., wall_seconds=7200., memory_mb=16384, query_wall_seconds=3600.),
    'W': W_LIMITS,
}


def hint_rows():
    facts = export_graph(ROOT / HINT_GRAPH, ROOT)['facts']
    return [(f['position'], f['outcome']) for f in facts.values()]


def build_golf(output, tiers=('A', 'B'), limits=None, targets=None):
    """Visible golf bundles sharing one hint file; ``targets`` overrides the
    panel with (tier, key, outcome, states) rows, e.g. for tests."""
    out = Path(output); out.mkdir()
    visible = out / 'visible'; visible.mkdir()
    rows = [r for r in (targets or GOLF_PANEL + GOLF_RESEARCH) if r[0] in tiers]
    digest = save(visible, encode(hint_rows()))
    base = snapshot()
    index = {'schema': 1, 'hints': digest, 'golf': []}
    for tier, target, outcome, states in rows:
        p = tuple(map(int, target.split(',')))
        from math import gcd
        from functools import reduce
        work = 'Root search' if reduce(gcd, p) == 1 else 'Recorded witness leaf'
        context = (f'Golf tier {tier}: the public database says {outcome}. Certify it independently; '
                   f'hints are untrusted and never cited. {work}: {states} native states.')
        m = manifest(p, base, verifier_profile(), execution_profile((limits or TIER_LIMITS)[tier]),
                     'golf', context, digest)
        ident = f'golf-{tier}-' + key(p).replace(',', '-')
        write(visible / (ident + '.json'), {'manifest': m, 'snapshot': base})
        index['golf'].append(ident)
    write(out / 'index.json', index)
    return index


def bundle_hints(bundle_path, bundle):
    digest = bundle['manifest'].get('hints')
    return str(path_for(Path(bundle_path).parent, digest)) if digest else None


def competitors():
    """The golf strategies, the hint-free golf-blind control, and the
    pre-existing interleaved search baseline for reference."""
    from .policies import BASELINES, GOLF
    chosen = {name: {'policy': p} for name, p in GOLF.items()}
    chosen['interleaved'] = {'policy': BASELINES['interleaved']}
    return chosen


def summarize(entries):
    """Per target: each competitor's median S, the lowest-S valid run, and
    the distinct valid certificates (by digest) with who produced them."""
    table = defaultdict(lambda: defaultdict(list)); best = {}; certificates = defaultdict(dict)
    for name, r in entries:
        k = key(r['position'])
        if r['status'] == 'valid':
            table[k][name].append(r['S'])
            certificates[k].setdefault(r['verification']['certificate_sha256'], name)
            if k not in best or r['S'] < best[k][1]['S']:
                best[k] = (name, r)
    medians = {k: {n: median(v) for n, v in rows.items()} for k, rows in table.items()}
    return medians, best, certificates


def golf_pilot(output, tiers=('A', 'B'), repeats=3, seed=0, workers=1, research_repeats=1):
    from .book import add_certificate, render_book
    from .tournament import render, run_tournament
    out = Path(output); out.mkdir()
    index = build_golf(out / 'fixtures', tiers)
    visible = out / 'fixtures' / 'visible'
    plan = {'schema': 1, 'tiers': list(tiers), 'repeats': repeats, 'research_repeats': research_repeats,
            'seed': seed, 'workers': workers, 'hints': index['hints'], 'targets': index['golf'],
            'competitors': competitors(),
            'scope': 'Public database results; golf measures certification cost, not discovery.'}
    write(out / 'plan.json', plan)
    entries = []
    for group, count in (('AB', repeats), ('C', research_repeats)):
        names = [n for n in index['golf'] if n.split('-')[1] in group]
        if not names:
            continue
        paths = [visible / (n + '.json') for n in names]
        bundles = [read(p) for p in paths]
        hints = {sha(b['manifest']): bundle_hints(p, b) for p, b in zip(paths, bundles)}
        entries += run_tournament(bundles, competitors(), out / f'tournament-{group}', out / 'tools',
                                  count, seed, hints=hints, workers=workers)
    medians, best, certificates = summarize(entries)
    book = out / 'book'
    directories = {}
    for group in ('AB', 'C'):
        tournament = out / f'tournament-{group}'
        if (tournament / 'runs.json').exists():
            for run in read(tournament / 'runs.json'):
                r = read(tournament / run['directory'] / 'receipt.json')
                if r['status'] == 'valid':
                    directories.setdefault(r['verification']['certificate_sha256'], (run['competitor'], tournament / run['directory']))
    # Every distinct valid certificate enters the Book; its deterministic
    # checking cost, not tournament S, picks each target's entry of record.
    for k in sorted(certificates):
        for digest in sorted(certificates[k]):
            name, directory = directories[digest]
            add_certificate(book, directory, out / 'tools', competitor=name, repeats=2)
    (book / 'BOOK.md').write_text(render_book(book))
    names = sorted(competitors())
    report = ['# Certificate golf pilot', '',
              'Every target is a public database result, so golf measures how cheaply a program can',
              '*certify* a known outcome, not discovery. Hints are untrusted: every certificate here was',
              'replayed by the fixed verifier with a fresh memo. S=(C+100)*(T+1), lower is better;',
              'T is discovery plus verification CPU seconds. golf-blind is the hint-free control; the',
              'interleaved search baseline is the pre-existing arena policy, whose fixed 0.6 s query',
              'slices are far below these targets\' root searches. No new mathematics is claimed.', '',
              '## Median S per target', '',
              '| Target | Tier | Outcome | Distinct certificates | ' + ' | '.join(names) + ' |',
              '| --- | --- | --- | ---: | ' + ' | '.join('---:' for _ in names) + ' |']
    panel = {t: (tier, o) for tier, t, o, _ in GOLF_PANEL + GOLF_RESEARCH}
    for k in sorted(medians, key=lambda k: (panel.get(k, ('?', ''))[0], k)):
        tier, o = panel.get(k, ('?', '?'))
        cells = [f'{medians[k][n]:.0f}' if n in medians[k] else '—' for n in names]
        report.append(f'| `{{{k}}}` | {tier} | {o} | {len(certificates[k])} | ' + ' | '.join(cells) + ' |')
    wins = defaultdict(int); choice = [k for k in medians if len(certificates[k]) > 1]
    for k in choice:
        wins[min(medians[k], key=medians[k].get)] += 1
    report += ['', '## Lowest median S where the certificates differ', '',
               f'{len(choice)} of {len(medians)} targets received more than one distinct certificate; on the',
               'others every competitor submitted the same proof, so their ordering is timing noise.', '']
    report += [f'- {n}: {wins[n]} of {len(choice)} targets' for n in names]
    report += ['', 'The Book for this pilot is in `book/BOOK.md`; per-run leaderboards follow.', '',
               render(entries, 'Golf leaderboards')]
    (out / 'REPORT.md').write_text('\n'.join(report) + '\n')
    write(out / 'summary.json', {'schema': 1, 'medians': medians, 'wins_where_certificates_differ': wins,
                                 'distinct_certificates': {k: len(v) for k, v in certificates.items()},
                                 'best': {k: {'competitor': n, 'S': r['S'], 'C': r['C'], 'T': r['T']}
                                          for k, (n, r) in best.items()}})
    return out / 'REPORT.md'


def w_book(output, book, workers=1, seed=0, strategies=('golf-witness', 'golf-root'), certificates=None, exclude=()):
    """Certify W's finitely certifiable obligations into ``book``.

    Targets already recorded in the Book (for example by the golf pilot's
    research tier) are not re-run. Every valid distinct certificate is
    admitted; the Book's entry of record decides between them.
    ``certificates`` is an optional directory of proof files from a longer
    curator search; each is admitted only after the Book's own replay.
    """
    from .book import add_certificate, render_book
    from .policies import GOLF
    from .tournament import run_tournament
    out = Path(output); out.mkdir()
    from .book import admit, admit_proof, measure
    from .exact import build_tools
    build_tools(out / 'tools')
    for path in sorted(Path(certificates).glob('*.json')) if certificates else ():
        admit_proof(book, read(path), out / 'tools', 'curator certificate', path.name, repeats=2)
    index = read(Path(book) / 'index.json') if (Path(book) / 'index.json').exists() else {'targets': {}}
    from .common import position
    skip = {key(position((*W, m))) for m in exclude}  # e.g. leaves too large to replay alongside other work
    rows = [r for r in w_targets() if r[1] not in index['targets'] and r[1] not in skip]
    if rows:
        fixture = build_golf(out / 'fixtures', ('W',), targets=rows)
        visible = out / 'fixtures' / 'visible'
        paths = [visible / (n + '.json') for n in fixture['golf']]
        bundles = [read(p) for p in paths]
        hints = {sha(b['manifest']): bundle_hints(p, b) for p, b in zip(paths, bundles)}
        chosen = {n: {'policy': GOLF[n]} for n in strategies}
        entries = run_tournament(bundles, chosen, out / 'tournament', out / 'tools', 1, seed, hints=hints, workers=workers)
        runs = read(out / 'tournament' / 'runs.json')
        seen = set()
        for (name, r), run in zip(entries, runs):
            if r['status'] != 'valid' or r['verification']['certificate_sha256'] in seen:
                continue
            seen.add(r['verification']['certificate_sha256'])
            add_certificate(book, out / 'tournament' / run['directory'], out / 'tools', competitor=name, repeats=2)
    # Obligations the campaign routed through infinite P positions: try a
    # bounded short-cover proof; admission re-verifies whatever is found.
    from .book import admit, measure
    from .exact import build_tools
    from .hints import Hints
    digest = save(out / 'hints', encode(hint_rows()))
    prover = ShortProver(Hints(path_for(out / 'hints', digest), digest), build_tools(out / 'tools'),
                         seconds=10., depth=2, max_queries=60)
    index = read(Path(book) / 'index.json') if (Path(book) / 'index.json').exists() else {'targets': {}}
    from .common import position
    index = read(Path(book) / 'index.json') if (Path(book) / 'index.json').exists() else {'targets': {}}
    for m in sorted(W_INFINITE):
        k = key(position((*W, m)))
        if k in index['targets'] or k in skip:
            continue
        nodes = prover.prove_n(position((*W, m)), 2)
        if nodes:
            proof = {'schema': 1, 'root': k, 'nodes': nodes}
            entry = measure(proof, out / 'tools', repeats=2)
            entry['source'] = {'competitor': 'short-cover prover (curator tool)'}
            admit(book, proof, entry)
    (Path(book) / 'BOOK.md').write_text(render_book(book))
    (Path(book) / 'W.md').write_text(render_w(book))
    return Path(book) / 'W.md'


def render_w(book):
    """All 52 obligations of W: Book-certified, finite witness, infinite dependency, or open."""
    from .common import position
    index = read(Path(book) / 'index.json')['targets']
    certified = 0
    if W_OPEN:
        status = (f'{52 - len(W_OPEN)} are covered. W itself remains unresolved: W P would establish '
                  'Q={16,26,88,98} N (Q + 62 = W), while U={16,26,88} P would still also need X={16,26,82,88} N.')
    else:
        status = ('all 52 are covered, so **W is P** ([campaign record](../../campaigns/w-p-2026-09-27/RESULT.md), '
                  'which lists what it rests on: the Quiet End Theorem and, through moves 12 and 36, three published '
                  'P-positions). Hence Q={16,26,88,98} is N (Q + 62 = W), and U={16,26,88} P now needs only '
                  'X={16,26,82,88} N.')
    lines = ['# The Book of W', '',
             'W = {16,26,62,98} is a node of the move-26 program. W is short, and its obligations are the 52 moves',
             'the Quiet End Theorem leaves: the 34 even moves 2g for the gaps g of its half {8,13,31,49}, and the',
             f"half's 18 odd gaps above 1; {status} This table records which coverings are",
             'self-contained certificates in The Book, replayed by the fixed verifier with a fresh memo and',
             'no inherited cache.', '',
             '| Move | Position | Status | Proof of record | C | States | V (s) |',
             '| ---: | --- | --- | --- | ---: | ---: | ---: |']
    for m in sorted([*W_WITNESSED, *W_FINITE, *W_INFINITE, *W_OPEN]):
        k = key(position((*W, m)))
        if m in W_OPEN:
            lines.append(f'| {m} | `{{{k}}}` | open | — | | | |')
        elif m in W_INFINITE and k not in index:
            reply, name = W_INFINITE[m]
            lines.append(f'| {m} | `{{{k}}}` | depends on {name} | reply {reply} | | | |')
        elif k in index:
            target = index[k]
            e = next(x for x in target['entries'] if x['certificate'] == target['record'])
            proof = read(Path(book) / 'certificates' / (e['certificate'] + '.json'))
            node = proof['nodes'][proof['root']]
            rule = f"reply {node['move']} → `{{{node['child']}}}`" if node['rule'] == 'edge' else 'finite leaf'
            if proof['nodes'].get(node.get('child'), {}).get('rule') == 'cover':
                rule += ' (Quiet End cover)'
            lines.append(f"| {m} | `{{{k}}}` | **Book** | {rule} | {e['C']} | {e['states']:,} | {e['V']:.3f} |")
            certified += 1
        elif m in W_WITNESSED:
            child = key(position((*W, m, W_WITNESSED[m])))
            lines.append(f'| {m} | `{{{k}}}` | finite witness, not yet in the Book | reply {W_WITNESSED[m]} → `{{{child}}}` | | | |')
        else:
            lines.append(f'| {m} | `{{{k}}}` | finite position, not yet in the Book | | | | |')
    depends = sum(1 for m in W_INFINITE if key(position((*W, m))) not in index)
    header = lines.index('| Move | Position | Status | Proof of record | C | States | V (s) |')
    pending = 52 - len(W_OPEN) - certified - depends
    lines[header:header] = [f'**{certified} of {52 - len(W_OPEN)} covered obligations** are certified here by self-contained '
                            'certificates; ' + (f'{pending} more have finite witnesses not yet in the Book; ' if pending else '')
                            + f'{depends} depend on infinite P positions outside the proof language (named in each row); '
                            + (f'{len(W_OPEN)} are open: {", ".join(map(str, W_OPEN))}.' if W_OPEN else 'none is open.'), '']
    return '\n'.join(lines) + '\n'


class ShortProver:
    """Build cover/edge/finite certificates for short gcd-two P positions.

    A curator tool for The Book, not a rated competitor: it consults hints
    first and falls back to bounded exact queries (the native solver, fresh
    memo) to find a finite witness for each child. Nothing it returns is
    trusted; admission re-verifies the whole certificate.
    """
    def __init__(self, hints, binary, odd_limit=301, seconds=120., depth=3, max_queries=200, seeds=None):
        self.hints, self.binary, self.odd_limit, self.seconds, self.depth = hints, binary, odd_limit, seconds, depth
        self.known = {}
        self.seeds = seeds or {}  # position key -> replies to try first (e.g. campaign records)
        self.queries = max_queries  # exact-query budget across the whole proof

    def outcome(self, p):
        from .common import profile
        k = key(p)
        if k in self.known:
            return self.known[k]
        o = self.hints.get(p)
        if o == 'unknown' and profile(p).get('frobenius', 1024) <= 1023 and self.queries > 0:
            self.queries -= 1
            import subprocess
            try:
                out = subprocess.run([str(self.binary), *map(str, p)], capture_output=True, text=True,
                                     timeout=self.seconds).stdout.split()
                o = out[0] if out and out[0] in ('P', 'N') else 'unknown'
            except subprocess.TimeoutExpired:
                o = 'unknown'
        self.known[k] = o
        return o

    def prove_p(self, p, depth=None):
        from .common import profile
        depth = self.depth if depth is None else depth
        info = profile(p)
        if info['gcd'] == 1:
            return {key(p): {'rule': 'finite', 'outcome': 'P'}} if self.outcome(p) == 'P' else None
        if not info['complete'] or depth == 0:
            return None
        nodes, rows = {}, []
        for m in info['moves']:
            child = self.prove_n(position_of(p, m), depth - 1)
            if child is None:
                return None
            nodes.update(child); rows.append({'move': m, 'child': key(position_of(p, m))})
        nodes[key(p)] = {'rule': 'cover', 'outcome': 'P', 'tail': info['tail'], 'children': rows}
        return nodes

    def prove_n(self, c, depth):
        from .common import profile
        info = profile(c)
        if info['gcd'] == 1:
            return {key(c): {'rule': 'finite', 'outcome': 'N'}} if self.outcome(c) == 'N' else None
        replies = list(info['moves']) + [r for r in range(3, self.odd_limit + 1, 2) if r not in info['moves']]
        seeded = [r for r in self.seeds.get(key(c), ()) if r in replies]
        replies = seeded + [r for r in replies if r not in seeded]
        finite = [r for r in replies if profile(position_of(c, r))['gcd'] == 1]
        # Seeds, then hinted finite witnesses, then exact search by increasing Frobenius.
        finite.sort(key=lambda r: (r not in seeded, self.hints.get(position_of(c, r)) != 'P',
                                   profile(position_of(c, r))['frobenius'], r))
        for r in finite:
            g = position_of(c, r)
            if self.outcome(g) == 'P':
                return {key(c): {'rule': 'edge', 'outcome': 'N', 'move': r, 'child': key(g)},
                        key(g): {'rule': 'finite', 'outcome': 'P'}}
        if depth > 0:  # depth counts cover levels; prove_p spends one
            for r in replies:
                g = position_of(c, r)
                if profile(g)['gcd'] != 1 and self.hints.get(g) == 'P':
                    sub = self.prove_p(g, depth)
                    if sub:
                        return {key(c): {'rule': 'edge', 'outcome': 'N', 'move': r, 'child': key(g)}, **sub}
        return None


def position_of(p, m):
    from .common import position
    return position((*p, m))
