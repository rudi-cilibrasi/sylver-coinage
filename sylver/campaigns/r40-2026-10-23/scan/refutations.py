"""Evidence for the finite refutations of answers to the reply 40: {16,40,a}+m is a finite P-position.

Usage: refutations.py A:M ... Each destination {16,40,a,m} is solved alone, sequentially
(kunz --threads 1, the state count native_solver.cpp would report). Writes evidence_16-40.json in collect.py's format (position [16,40]; each row an
answer a as the obligation and m as its reply), for replay.py.
"""
import json, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position  # noqa: E402

HERE = Path(__file__).resolve().parent
BASE = (16, 40)


def main(pairs):
    rows = []
    for a, m in pairs:
        child = position((*BASE, a))
        assert legal(position(BASE), a) and legal(child, m)
        dest = position((*child, m))
        start = time.monotonic()
        line = subprocess.run([str(HERE / 'kunz'), '--threads', '1', *map(str, dest)], capture_output=True,
                              text=True, check=True).stdout.split()
        assert line[0] == 'P', (a, m, line)
        row = {'obligation': a, 'kind': 'even', 'reply': m, 'via': 'finite', 'destination': key(dest),
               'frobenius': int(line[2].split('=')[1]), 'states': int(line[3].split('=')[1]),
               'seconds': round(time.monotonic() - start, 1)}
        rows.append(row)
        print(json.dumps(row), flush=True)
    (HERE / 'evidence_16-40.json').write_text(json.dumps({'position': list(BASE), 'rows': rows}, indent=1))


if __name__ == '__main__':
    main([tuple(map(int, x.split(':'))) for x in sys.argv[1:]])
