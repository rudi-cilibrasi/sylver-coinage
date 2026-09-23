"""Canonical encodings and finite/short position profiles."""
import hashlib
import json
from math import gcd
from pathlib import Path

from sylver.short_certificates import is_generated, minimal_generators
from sylver.solver import FiniteSolver

SCHEMA = 1
THEOREMS = ('quiet-end-v1',)
ROOT = Path(__file__).resolve().parents[2]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def decode(text):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError(f'duplicate JSON key: {k}')
            result[k] = v
        return result
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def read(path):
    return decode(Path(path).read_text())


def write(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_bytes(canonical(value) + b'\n')
    tmp.replace(path)


def fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise ValueError(f'expected fields {required}; got {value!r}')


def integer(value, minimum=0, maximum=100000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('integer outside supported profile')
    return value


def position(values):
    if not isinstance(values, (list, tuple)) or not values or len(values) > 128:
        raise ValueError('expected nonempty generator list')
    for v in values:
        integer(v, 2, 4096)
    # Shift-and-union closure is the same semigroup operation used by the
    # reference finite solver. It avoids quadratic repeated DP during import
    # of the 305,011-row baseline; arbitrary gcd is supported here.
    result=[];bits=1;mask=(1<<(max(values)+1))-1
    for v in sorted(set(values)):
        if bits & (1<<v):continue
        result.append(v);shift=v
        while shift<=max(values):
            bits|=(bits<<shift)&mask;shift*=2
    return tuple(result)


def key(values):
    return ','.join(map(str, position(values)))


def from_key(value):
    if not isinstance(value, str):
        raise ValueError('position key must be a string')
    p = position([int(x) for x in value.split(',')])
    if key(p) != value:
        raise ValueError('noncanonical position key')
    return p


def profile(values):
    p = position(values)
    d = gcd(*p)
    result = dict(position=list(p), gcd=d, complete=False, moves=[], tail='unsupported')
    if d == 1:
        solver = FiniteSolver(p)
        result.update(complete=True, moves=list(solver.legal_moves(solver.initial_state)),
                      tail='finite', frobenius=solver.frobenius)
    elif d == 2 and p != (2,):
        half = FiniteSolver(tuple(x // 2 for x in p))
        even = [2*x for x in half.gaps()]
        quiet = half.is_quiet_ender()
        odds = [x for x in half.gaps() if x > 1 and x % 2] if quiet else []
        result.update(complete=quiet, moves=sorted(even+odds), even_moves=even,
                      tail='quiet-end-v1' if quiet else 'unproved-infinite-odd-tail',
                      half_frobenius=half.frobenius)
    return result


def legal(p, move):
    integer(move, 2, 4096)
    return not is_generated(p, move)
