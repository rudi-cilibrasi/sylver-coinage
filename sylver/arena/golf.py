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
# W={16,26,62,98} has 52 obligations; 47 are covered. Each covered move m
# is refuted by a recorded reply. For these 35 the refutation is a finite
# certificate: even moves (gcd two) by an odd witness reaching a finite P
# position, odd moves by a finite N position itself (the verifier finds its
# winning move). Witnesses: campaign graph and the plan2 release certificate.
W = (16, 26, 62, 98)
W_WITNESSED = {2: 3, 18: 5, 19: 23, 22: 15, 27: 19, 28: 25, 30: 111, 34: 39, 38: 55, 40: 11, 44: 19, 46: 17,
               50: 29, 54: 33, 60: 27, 67: 31, 76: 43, 82: 27, 102: 95, 134: 85}
W_FINITE = (3, 5, 7, 9, 11, 15, 17, 23, 25, 33, 35, 41, 43, 51, 59)
# The other 12 covered moves reach infinite P positions, whose own
# certificates are campaign or published results outside this proof set.
W_INFINITE = {4: (6, '{4,6}'), 6: (4, '{4,6}'), 8: (20, 'G={8,20,26}'), 10: (24, 'K={10,16,24}'),
              12: (14, '{12,14,16}'), 14: (12, '{12,14,16}'), 20: (8, 'G={8,20,26}'),
              24: (10, 'K={10,16,24}'), 36: (56, 'V={16,26,36,56}'), 56: (36, 'V={16,26,36,56}'),
              66: (56, 'B={16,26,56,62,66}'), 72: (82, '{16,26,62,72,82} (Sicherman, published)')}
W_OPEN = (70, 86, 92, 108, 118)
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


def w_book(output, book, workers=1, seed=0, strategies=('golf-witness', 'golf-root')):
    """Certify W's finitely certifiable obligations into ``book``.

    Targets already recorded in the Book (for example by the golf pilot's
    research tier) are not re-run. Every valid distinct certificate is
    admitted; the Book's entry of record decides between them.
    """
    from .book import add_certificate, render_book
    from .policies import GOLF
    from .tournament import run_tournament
    out = Path(output); out.mkdir()
    index = read(Path(book) / 'index.json') if (Path(book) / 'index.json').exists() else {'targets': {}}
    rows = [r for r in w_targets() if r[1] not in index['targets']]
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
            add_certificate(book, out / 'tournament' / run['directory'], out / 'tools', competitor=name)
    (Path(book) / 'BOOK.md').write_text(render_book(book))
    (Path(book) / 'W.md').write_text(render_w(book))
    return Path(book) / 'W.md'


def render_w(book):
    """All 52 obligations of W: Book-certified, infinite dependency, or open."""
    from .common import position
    index = read(Path(book) / 'index.json')['targets']
    certified = 0
    lines = ['# The Book of W', '',
             'W = {16,26,62,98} is a node of the move-26 program: W P would establish Q={16,26,88,98} N',
             '(Q + 62 = W), while U={16,26,88} P would still also need X={16,26,82,88} N. W is short: its',
             'obligations are its 52 moves below the Quiet End bound. 47 are covered; this table records',
             'which coverings are self-contained certificates in The Book, replayed by the fixed verifier',
             'with a fresh memo and no inherited cache. W itself remains unresolved.', '',
             '| Move | Position | Status | Proof of record | C | States | V (s) |',
             '| ---: | --- | --- | --- | ---: | ---: | ---: |']
    for m in sorted([*W_WITNESSED, *W_FINITE, *W_INFINITE, *W_OPEN]):
        k = key(position((*W, m)))
        if m in W_OPEN:
            lines.append(f'| {m} | `{{{k}}}` | open | — | | | |')
        elif m in W_INFINITE:
            reply, name = W_INFINITE[m]
            lines.append(f'| {m} | `{{{k}}}` | depends on {name} | reply {reply} | | | |')
        elif k in index:
            target = index[k]
            e = next(x for x in target['entries'] if x['certificate'] == target['record'])
            proof = read(Path(book) / 'certificates' / (e['certificate'] + '.json'))
            node = proof['nodes'][proof['root']]
            rule = f"reply {node['move']} → `{{{node['child']}}}`" if node['rule'] == 'edge' else 'finite leaf'
            lines.append(f"| {m} | `{{{k}}}` | **Book** | {rule} | {e['C']} | {e['states']:,} | {e['V']:.3f} |")
            certified += 1
        else:
            lines.append(f'| {m} | `{{{k}}}` | finitely certifiable, not yet in the Book | | | | |')
    lines[6:6] = [f'**{certified} of 47 covered obligations** are certified here; '
                  f'{len(W_INFINITE)} depend on infinite P positions (named below each row); '
                  f'{len(W_OPEN)} are open: {", ".join(map(str, W_OPEN))}.', '']
    return '\n'.join(lines) + '\n'
