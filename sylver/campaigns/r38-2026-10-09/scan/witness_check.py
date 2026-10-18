"""Check each witness in hunt.jsonl (a row C+w found P) against the hunt's other rows.

Two P-positions are never one move apart, so a witness P = C+w is inconsistent with the rows if
- a row says C+x is N with winning move w, and x is legal in P (then C+x+w = P+x is P, one move
  from P; when x is generated in P, C+x+w is P itself, which is how hunt.py's partner rule finds
  a witness), or
- a P-position the rows name (C+w of a P row, C+x+v of an N row won by v) is one move from P,
  either way.
Also prints the witness's rank, counting from 0, among C's odd replies up to 801 in hunt.py's
order (by the Frobenius number of C plus the reply), or "beyond" for a reply past 801.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from sylver.arena.common import legal, position  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

HERE = Path(__file__).resolve().parent
WMAX = 801
rows = [json.loads(line) for line in (HERE / 'hunt.jsonl').read_text().splitlines()]
named = set()
for r in rows:
    if r['outcome'] == 'P':
        named.add(position((*r['child'], r['w'])))
    elif r['outcome'] == 'N' and str(r['winning_move']).isdigit():
        named.add(position((*r['child'], r['w'], int(r['winning_move']))))


def one_move(a, b):
    """b is a's position after one legal move."""
    return any(legal(a, g) and position((*a, g)) == b for g in b)


print(f'{len(named)} P-positions named by {len(rows)} rows')
bad = 0
for r in rows:
    if r['outcome'] != 'P':
        continue
    c, w = tuple(r['child']), r['w']
    p = position((*c, w))
    won_by_w = [x['w'] for x in rows if tuple(x['child']) == c and x['outcome'] == 'N'
                and str(x['winning_move']) == str(w) and legal(p, x['w'])]
    near = [q for q in named if q != p and (one_move(p, q) or one_move(q, p))]
    order = sorted((x for x in range(3, WMAX + 1, 2) if legal(c, x)),
                   key=lambda x: (frobenius_number(position((*c, x))), x))
    ok = not won_by_w and not near
    bad += not ok
    print(f'{list(c)}+{w}: frobenius={frobenius_number(p)}'
          f' rank={order.index(w) if w in order else "beyond"} of {len(order)}'
          f' won_by_w={won_by_w} one_move={near} {"ok" if ok else "INCONSISTENT"}')
sys.exit(1 if bad else 0)
