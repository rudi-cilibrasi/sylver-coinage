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

# Predeclared panel: a seeded draw (random.Random(20260927)) from the cache by
# Frobenius band, accepted by the deterministic native root-search state
# count (tier A at most 2M states; tier B 0.5M-8M) so that proof structure,
# not process start-up, dominates. (tier, target, public outcome, states)
GOLF_PANEL = (
    ('A', '16,26,34,38,40,113,123,125,135', 'N', 1214833),
    ('A', '16,26,36,38,40,44,46,115,133,135,139,145', 'N', 1000046),
    ('A', '16,26,28,36,38,46,111,121,131,133,135', 'N', 764240),
    ('A', '16,26,30,38,109,123,127,137', 'P', 1876804),
    ('A', '16,26,28,30,38,79', 'P', 448489),
    ('A', '16,20,26,28,38,111,121,129,135', 'P', 169082),
    ('B', '16,26,38,44,50,119,129,137,139,147,149', 'N', 4577786),
    ('B', '16,26,28,38,50,113,147,149', 'N', 1419193),
    ('B', '16,26,28,36,38,46,117,137', 'N', 828475),
    ('B', '16,26,38,44,46,56,111,129,131,133', 'P', 3330318),
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
TIER_LIMITS = {
    'A': dict(DEFAULT_LIMITS, cpu_seconds=600., wall_seconds=1800., memory_mb=8192, query_wall_seconds=600.),
    'B': dict(DEFAULT_LIMITS, cpu_seconds=600., wall_seconds=1800., memory_mb=8192, query_wall_seconds=600.),
    'C': dict(DEFAULT_LIMITS, cpu_seconds=3600., wall_seconds=7200., memory_mb=16384, query_wall_seconds=3600.),
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
        context = (f'Golf tier {tier}: the public database says {outcome}. Certify it independently; '
                   f'hints are untrusted and never cited. Root search: {states} native states.')
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
    from .policies import BASELINES, GOLF
    chosen = {name: {'policy': p} for name, p in GOLF.items()}
    for name in ('interleaved', 'increasing'):
        chosen[name] = {'policy': BASELINES[name]}
    return chosen


def summarize(entries):
    """Per target: each competitor's median S and the lowest-S valid run."""
    table = defaultdict(lambda: defaultdict(list)); best = {}
    for name, r in entries:
        k = key(r['position'])
        if r['status'] == 'valid':
            table[k][name].append(r['S'])
            if k not in best or r['S'] < best[k][1]['S']:
                best[k] = (name, r)
    medians = {k: {n: median(v) for n, v in rows.items()} for k, rows in table.items()}
    return medians, best


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
    medians, best = summarize(entries)
    book = out / 'book'
    for k, (name, r) in sorted(best.items()):
        directory = next(p for p in out.glob('tournament-*/*') if p.is_dir() and (p / 'receipt.json').exists()
                         and sha(read(p / 'receipt.json')) == sha(r))
        add_certificate(book, directory, out / 'tools', competitor=name)
    (book / 'BOOK.md').write_text(render_book(book))
    report = ['# Certificate golf pilot', '',
              'Every target is a public database result, so golf measures how cheaply a program can',
              '*certify* a known outcome, not discovery. Hints are untrusted: every certificate here was',
              'replayed by the fixed verifier with a fresh memo. S=(C+100)*(T+1), lower is better;',
              'T is discovery plus verification CPU seconds. No new mathematics is claimed.', '',
              '## Median S per target', '',
              '| Target | Tier | Outcome | ' + ' | '.join(sorted(competitors())) + ' |',
              '| --- | --- | --- | ' + ' | '.join('---:' for _ in competitors()) + ' |']
    panel = {t: (tier, o) for tier, t, o, _ in GOLF_PANEL + GOLF_RESEARCH}
    for k in sorted(medians, key=lambda k: (panel.get(k, ('?', ''))[0], k)):
        tier, o = panel.get(k, ('?', '?'))
        cells = [f'{medians[k][n]:.0f}' if n in medians[k] else '—' for n in sorted(competitors())]
        report.append(f'| `{{{k}}}` | {tier} | {o} | ' + ' | '.join(cells) + ' |')
    wins = defaultdict(int)
    for k, rows in medians.items():
        wins[min(rows, key=rows.get)] += 1
    report += ['', '## Lowest median S by target', '']
    report += [f'- {n}: {wins[n]} of {len(medians)} targets' for n in sorted(competitors())]
    report += ['', 'The Book for this pilot is in `book/BOOK.md`; per-run leaderboards follow.', '',
               render(entries, 'Golf leaderboards')]
    (out / 'REPORT.md').write_text('\n'.join(report) + '\n')
    write(out / 'summary.json', {'schema': 1, 'medians': medians, 'wins': wins,
                                 'best': {k: {'competitor': n, 'S': r['S'], 'C': r['C'], 'T': r['T']}
                                          for k, (n, r) in best.items()}})
    return out / 'REPORT.md'
