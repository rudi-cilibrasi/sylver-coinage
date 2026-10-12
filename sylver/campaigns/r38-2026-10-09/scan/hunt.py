"""Round-robin witness hunt for several long gcd-two children C: the first odd w with C+w P.

Each reply is solved alone (kunz --stop-at-p --odd-list w C...) with a state cap, so hard
replies are classified rather than skipped. The partner rule: when C+w is N with an odd
winning reply v and w is a legal move of C+v, then {C,w,v} is P and C+v is N (winning
reply w), so v needs no solve; if w is not legal there, C+v = {C,w,v} is P (a witness,
logged as a P row with 'via').
Appends one JSON line per reply to hunt.jsonl; a child stops at its first witness.

Usage: hunt.py CAP [--retry-capped]  (the children and their starting points are in CHILDREN below)
With --retry-capped, each child's queue is instead the replies earlier runs left at a smaller
cap, in the same order, each tried once at CAP. Rows record their cap; rows without one ran at
1.2e9 (October 10, 03:55 to 07:32) or 1e9, and count as 1e9 here, below any retry cap.
"""
import json, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import legal, position  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

HERE = Path(__file__).resolve().parent
CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000_000
RETRY = '--retry-capped' in sys.argv[2:]
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


def start(c, spec):
    """A child's state from its spec and the records: its witness, if found, and the replies left."""
    mine = [r for r in records if tuple(r['child']) == c]
    witness = next((r['w'] for r in mine if r['outcome'] == 'P'), None)
    if RETRY:                   # replies capped below CAP and never classified
        settled = {r['w'] for r in mine if r['outcome'] is not None}
        at_cap = {r['w'] for r in mine if r['outcome'] is None and r.get('cap', 1_000_000_000) >= CAP}
        lower = {r['w'] for r in mine if r['outcome'] is None} - settled - at_cap
        state[c] = {'queue': sorted(lower, key=order_key(c)), 'witness': witness}
    else:
        classified = {r['w'] for r in mine}
        state[c] = {'queue': [w for w in queue(c, spec) if w not in classified], 'witness': witness}
    for r in records:
        if tuple(r['child']) == c and r['outcome'] == 'N' and r.get('winning_move') and int(r['winning_move']) % 2:
            v = int(r['winning_move'])
            if v in state[c]['queue'] and legal(position((*c, v)), r['w']):
                state[c]['queue'].remove(v)


for c, spec in CHILDREN.items():
    start(c, spec)


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
        start(c, {k: v for k, v in row.items() if k != 'child'})
        print(time.strftime('%H:%M:%S'), 'added child', c, 'queue', len(state[c]['queue']),
              'witness', state[c]['witness'], flush=True)


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
               'returncode': proc.returncode, 'seconds': round(time.monotonic() - start, 1), 'cap': CAP}
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
                else:                   # C+v = C+w+v as semigroups, and C+w+v is P
                    s['witness'] = v
                    s['queue'].remove(v)
                    log({'child': list(c), 'w': v, 'outcome': 'P', 'winning_move': None, 'states': None,
                         'via': f'partner of {w}: {w} is generated in C+{v}, so C+{v} = C+{w}+{v}'})
                    print('WITNESS (partner)', c, v, flush=True)
        elif rec['outcome'] is None and not RETRY:
            s['queue'].append(w)   # hit the cap: retry last
for c, s in state.items():
    print('child', c, 'witness', s['witness'], 'queue left', len(s['queue']), flush=True)
