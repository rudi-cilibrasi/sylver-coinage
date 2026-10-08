"""Evidence table for a short position: every obligation, its answer, and the answer's size.

Odd obligations m: one verified kunz sweep of P+m gives each N row's winning reply w.
Even obligations e: the resolver's reply (even_<r>.jsonl; node or finite odd witness).
Every finite destination is then solved alone, sequentially (kunz --threads 1, the
state count native_solver.cpp would report). Writes evidence_<r>.json.
"""
import json, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position, profile  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

HERE = Path(__file__).resolve().parent
ENGINE = str(HERE / 'kunz')


def run(*args, timeout=None):
    return subprocess.run([ENGINE, *map(str, args)], capture_output=True, text=True, check=True, timeout=timeout).stdout


def main(generators, resolved_file, overrides):
    base = position(tuple(generators))
    r = '-'.join(map(str, base))
    info = profile(base)
    assert info['complete'] and info['tail'] == 'quiet-end-v1'
    odd = [m for m in info['moves'] if m % 2]
    even = [m for m in info['moves'] if m % 2 == 0]
    rows = []
    out = run('--threads', 8, '--verify-memo', '--odd-list', ','.join(map(str, odd)), *base)
    assert out.splitlines()[-1].startswith('verified entries='), out[-200:]
    for line in out.splitlines()[:-1]:
        parts = line.split()
        m, outcome, w = int(parts[0].split('=')[1]), parts[1], parts[2].split('=')[1]
        assert outcome == 'N', line
        rows.append({'obligation': m, 'kind': 'odd', 'reply': int(w), 'via': 'finite'})
    resolved = {json.loads(l)['e']: json.loads(l) for l in (HERE / resolved_file).read_text().splitlines()}
    for e in even:
        row = resolved.get(e)
        if str(e) in overrides:   # an answer into another position this campaign certifies
            reply, via = overrides[str(e)]
            rows.append({'obligation': e, 'kind': 'even', 'reply': reply, 'via': via})
            continue
        if row is None or row['status'] != 'resolved':
            raise AssertionError(f'obligation {e} unresolved')
        else:
            via = row['via']
            rows.append({'obligation': e, 'kind': 'even', 'reply': row['reply'],
                         'via': via.split()[-1] if via.startswith('node') else 'finite'})
    for row in rows:
        child = position((*base, row['obligation']))
        assert legal(base, row['obligation']) and legal(child, row['reply'])
        dest = position((*child, row['reply']))
        row['destination'] = key(dest)
        if row['via'] == 'finite':
            start = time.monotonic()
            row['seconds'] = 0
            line = run('--threads', 1, *dest).split()
            assert line[0] == 'P', (row, line)
            row.update(frobenius=int(line[2].split('=')[1]), states=int(line[3].split('=')[1]),
                       seconds=round(time.monotonic() - start, 1))
        print(json.dumps(row), flush=True)
    (HERE / f'evidence_{r}.json').write_text(json.dumps({'position': list(base), 'obligations': len(info['moves']),
                                                        'rows': rows}, indent=1))
    big = sorted((x for x in rows if x['via'] == 'finite'), key=lambda x: -x['states'])[:8]
    print('largest destinations:', [(x['obligation'], x['reply'], f"{x['states']:,}") for x in big], flush=True)


if __name__ == '__main__':
    # collect.py RESOLVED_FILE OVERRIDES_JSON GENERATOR...
    main([int(x) for x in sys.argv[3:]], sys.argv[1], json.loads(sys.argv[2]))
