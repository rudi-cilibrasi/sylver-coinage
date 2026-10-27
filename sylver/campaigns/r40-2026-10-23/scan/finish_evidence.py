"""Finish B66's evidence file after collect.py stopped during its move 90.

collect.py (collect_B66.log) wrote a row for each of B66={16,40,44,66}'s 24 odd obligations and its even ones up
to 86, then solved move 90's destination {16,40,44,66,90,463} alone until guard90.sh stopped it (guard90.log).
This takes those rows, adds 90 unsized, solves the destinations of 94, 102, 118 and 134 alone as collect.py does
(kunz --threads 1), and writes evidence_16-40-44-66.json in collect.py's format.
"""
import json, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position, profile  # noqa: E402

HERE = Path(__file__).resolve().parent
base = position((16, 40, 44, 66))
info = profile(base)
rows = [json.loads(line) for line in (HERE / 'collect_B66.log').read_text().splitlines() if line.startswith('{')]
done = {row['obligation'] for row in rows}
resolved = {json.loads(l)['e']: json.loads(l) for l in (HERE / 'resolve_16-40-44-66.jsonl').read_text().splitlines()}
replies = {90: 463, 134: 181}
for e in [m for m in info['moves'] if m % 2 == 0 and m not in done]:
    reply = replies.get(e) or resolved[e]['reply']
    assert e in replies or resolved[e]['via'] == 'finite odd witness', (e, resolved[e])
    child = position((*base, e))
    assert legal(base, e) and legal(child, reply)
    dest = position((*child, reply))
    row = {'obligation': e, 'kind': 'even', 'reply': reply, 'via': 'finite', 'destination': key(dest)}
    if e == 90:
        row.update(frobenius=None, states=None,
                   note='not sized: solved alone (kunz --threads 1) from 20:12 until guard90.sh stopped it at 21:45, '
                        'at 32,301,908 kB RSS (guard90.log)')
    else:
        start = time.monotonic()
        line = subprocess.run([str(HERE / 'kunz'), '--threads', '1', *map(str, dest)], capture_output=True, text=True,
                              check=True).stdout.split()
        assert line[0] == 'P', (row, line)
        row.update(frobenius=int(line[2].split('=')[1]), states=int(line[3].split('=')[1]),
                   seconds=round(time.monotonic() - start, 1))
    print(json.dumps(row), flush=True)
    rows.append(row)
assert sorted(row['obligation'] for row in rows) == info['moves']
(HERE / 'evidence_16-40-44-66.json').write_text(json.dumps({'position': list(base), 'obligations': len(info['moves']),
                                                            'rows': rows}, indent=1))
finite = [row for row in rows if row['via'] == 'finite']
sized = [row for row in finite if row['states'] is not None]
print('finite:', len(finite), 'sized:', len(sized), 'states:', f"{sum(row['states'] for row in sized):,}",
      'routes:', sorted((row['obligation'], row['via']) for row in rows if row['via'] != 'finite'), flush=True)
