"""Round-robin witness hunt for several long gcd-two children C: the first odd w with C+w P.

Each reply is solved alone (kunz --stop-at-p --odd-list w C...) with a state cap, so hard
replies are classified rather than skipped. The partner rule: when C+w is N with an odd
winning reply v and w is a legal move of C+v, then {C,w,v} is P and C+v is N (winning
reply w), so v needs no solve; if w is not legal there, C+v = {C,w,v} is P (a witness).
Appends one JSON line per reply to hunt.jsonl; a child stops at its first witness.

Usage: hunt.py CAP  (the children and their starting points are in CHILDREN below)
"""
import json, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import legal, position  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

HERE = Path(__file__).resolve().parent
CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000_000
WMAX = 801
# child: (replies already classified N, by count of the resolver's Frobenius order or explicitly)
CHILDREN = {
    (16, 38, 68, 72): dict(after=171, also=[153, 161, 165, 169, 171]),
    (16, 38, 72, 78): dict(done_count=47, also=[]),
    (16, 38, 72, 84): dict(done_count=53, also=[]),
    (16, 38, 72, 100): dict(done_count=41, also=[65, 77, 79, 83]),
    (16, 38, 72, 106): dict(done_count=41, also=[71, 75, 81, 83]),
}
LOG = HERE / 'hunt.jsonl'


def order_key(c):
    return lambda w: (frobenius_number(position((*c, w))), w)


def queue(c, spec):
    key = order_key(c)
    odd = [w for w in range(3, WMAX + 1, 2) if legal(c, w)]
    if 'done_count' in spec:
        done = set(sorted((w for w in odd if w <= 401), key=key)[:spec['done_count']])
        rest = [w for w in odd if w not in done]
    else:
        rest = [w for w in odd if w > spec['after']]
    return sorted(set(rest) | set(spec['also']), key=key)


records = [json.loads(l) for l in LOG.read_text().splitlines()] if LOG.exists() else []
state = {}
for c, spec in CHILDREN.items():
    classified = {r['w'] for r in records if tuple(r['child']) == c}
    witness = next((r['w'] for r in records if tuple(r['child']) == c and r['outcome'] == 'P'), None)
    state[c] = {'queue': [w for w in queue(c, spec) if w not in classified], 'witness': witness}
    for r in records:
        if tuple(r['child']) == c and r['outcome'] == 'N' and r.get('winning_move') and int(r['winning_move']) % 2:
            v = int(r['winning_move'])
            if v in state[c]['queue'] and legal(position((*c, v)), r['w']):
                state[c]['queue'].remove(v)


def log(rec):
    with LOG.open('a') as fh:
        fh.write(json.dumps(rec) + '\n')
    print(time.strftime('%H:%M:%S'), rec['child'], rec['w'], rec['outcome'], rec.get('winning_move'),
          rec.get('states'), rec.get('via', ''), flush=True)


def load_extra():
    extra = HERE / 'hunt_children.json'
    if not extra.exists():
        return
    for row in json.loads(extra.read_text()):
        c = tuple(row['child'])
        if c in state:
            continue
        spec = {k: v for k, v in row.items() if k != 'child'}
        classified = {r['w'] for r in records if tuple(r['child']) == c}
        state[c] = {'queue': [w for w in queue(c, spec) if w not in classified], 'witness': None}
        print(time.strftime('%H:%M:%S'), 'added child', c, 'queue', len(state[c]['queue']), flush=True)


load_extra()
while any(s['witness'] is None and s['queue'] for s in state.values()):
    load_extra()
    for c, s in list(state.items()):
        if s['witness'] is not None or not s['queue']:
            continue
        w = s['queue'].pop(0)
        start = time.monotonic()
        proc = subprocess.run([str(HERE / 'kunz'), '--threads', '6', '--stop-at-p', '--max-states', str(CAP),
                               '--odd-list', str(w), *map(str, c)], capture_output=True, text=True)
        rows = [l.split() for l in proc.stdout.splitlines() if l.startswith('move=')]
        rec = {'child': list(c), 'w': w, 'outcome': rows[0][1] if rows else None,
               'winning_move': rows[0][2].split('=')[1] if rows else None,
               'states': int(rows[0][4].split('=')[1]) if rows else None,
               'returncode': proc.returncode, 'seconds': round(time.monotonic() - start, 1)}
        log(rec)
        if rec['outcome'] == 'P':
            s['witness'] = w
            print('WITNESS', c, w, flush=True)
        elif rec['outcome'] == 'N' and rec['winning_move'] and rec['winning_move'] != 'none':
            v = int(rec['winning_move'])
            if v % 2 and v in s['queue']:
                if legal(position((*c, v)), w):
                    s['queue'].remove(v)
                    log({'child': list(c), 'w': v, 'outcome': 'N', 'winning_move': str(w), 'states': None,
                         'via': f'partner of {w}'})
                else:
                    s['witness'] = v
                    print('WITNESS (partner)', c, v, flush=True)
        elif rec['outcome'] is None:
            s['queue'].append(w)   # hit the cap: retry last
for c, s in state.items():
    print('child', c, 'witness', s['witness'], 'queue left', len(s['queue']), flush=True)
