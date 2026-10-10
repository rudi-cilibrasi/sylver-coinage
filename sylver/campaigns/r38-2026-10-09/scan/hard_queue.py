"""Test each hard (previously skipped) odd reply alone with a large memo, child by child.

For each child C and its list of replies (in order), run kunz --stop-at-p on C+w alone with
--max-states CAP; stop the child's list at its first P. Appends JSON lines to hard_queue.jsonl.
"""
import json, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import legal, position  # noqa: E402

HERE = Path(__file__).resolve().parent
CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 1_400_000_000
QUEUE = [
    ((16, 38, 72, 78), [81, 87, 91, 93, 95]),
    ((16, 38, 72, 84), [87, 99, 101, 105, 107]),
    ((16, 38, 68, 72), [147, 153, 161, 165, 169, 171]),
]
out = HERE / 'hard_queue.jsonl'
records = [json.loads(l) for l in out.read_text().splitlines()] if out.exists() else []
done = {(tuple(r['child']), r['w']) for r in records}
# Partner rule: if C+w is N with the odd winning reply v, then {C,w,v} is P. If w is a legal
# move of C+v, then C+v is N too (its winning reply is w); if it is not, C+v = {C,w,v} is P.
def partner_ok(child, w, v):
    return legal(position((*child, v)), w)

partners = {(tuple(r['child']), int(r['winning_move'])) for r in records
            if r['outcome'] == 'N' and r['winning_move'] and int(r['winning_move']) % 2
            and partner_ok(tuple(r['child']), r['w'], int(r['winning_move']))}
for child, ws in QUEUE:
    for w in ws:
        if (child, w) in done:
            continue
        if (child, w) in partners:
            print(time.strftime('%H:%M:%S'), child, w, 'N by the partner rule (skipped)', flush=True)
            continue
        start = time.monotonic()
        proc = subprocess.run([str(HERE / 'kunz'), '--threads', '6', '--stop-at-p', '--max-states', str(CAP),
                               '--odd-list', str(w), *map(str, child)], capture_output=True, text=True)
        rows = [l.split() for l in proc.stdout.splitlines() if l.startswith('move=')]
        outcome = rows[0][1] if rows else None
        rec = {'child': list(child), 'w': w, 'outcome': outcome,
               'winning_move': rows[0][2].split('=')[1] if rows else None,
               'states': int(rows[0][4].split('=')[1]) if rows else None,
               'returncode': proc.returncode, 'stderr_tail': proc.stderr[-200:],
               'seconds': round(time.monotonic() - start, 1)}
        with out.open('a') as fh:
            fh.write(json.dumps(rec) + '\n')
        print(time.strftime('%H:%M:%S'), child, w, outcome, rec['states'], rec['seconds'], flush=True)
        if outcome == 'P':
            print('WITNESS', child, w, flush=True)
            break
        if outcome == 'N' and rec['winning_move'] and int(rec['winning_move']) % 2:
            v = int(rec['winning_move'])
            if partner_ok(child, w, v):
                partners.add((child, v))
            else:
                print('WITNESS (partner)', child, v, flush=True)
