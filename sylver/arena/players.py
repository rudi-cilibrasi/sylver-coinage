"""Built-in game players and the line-protocol host they share.

``python -m sylver.arena.players NAME [--seed S] [--options JSON]`` plays over
stdin/stdout exactly as an external program would; stdout carries protocol
lines only. Play is deterministic given the seed and options, except that the
exact players stop searching when their per-move CPU budget ends. A claim is
the player's own view of the uncapped game; the referee never relies on it.
"""
import argparse
import json
import os
import random
import re
import resource
import subprocess
import sys

from sylver.solver import solve_position

from .common import ROOT
from .game import Position, _adjoin, minimal_generators

VERSION = '1'
CACHE = ROOT / 'sylver/move26_data/periodicity_x.cache'
NATIVE = re.compile(r'([PN]) winning_move=(none|\d+) frobenius=\d+ states=\d+')
# Uncapped-game P-positions (canonical keys) with their sources; load_book
# adds {p} for primes 5 <= p <= max_move (Hutchings).
THEORY = (
    ('2,3', 'terminal: the player to move must name 1'),
    ('4,6', 'classical (Winning Ways)'),
    ('8,12', 'Blok'),
    ('8,10,22', 'Sicherman'),
    ('12,16,22', 'published; independently confirmed here'),
    ('16,20,34', 'published; independently confirmed here'),
    ('10,16,24', 'published; independently confirmed here'),
    ('16,26,36,56', "Sicherman's table; certified here"),
    ('16,26,56,62,66', 'B, PR #4'),
    ('16,26,62,85,98,134', 'W move 134, reply 85, PR #5'),
    ('16,26,62,95,98,102', 'W move 102, reply 95, PR #13'),
    ('16,26,62,86,98,129', 'W move 86, reply 129, PR #21'),
    ('16,26,62,92,98,139', 'W move 92, reply 139, PR #21'),
    ('16,26,62,70,98,169', 'W move 70, reply 169, PR #24'),
    ('16,26,62,98,118,167', 'W move 118, reply 167, PR #27'),
    ('16,26,62,98,108,213', 'W move 108, reply 213, PR #28'),
    ('16,26,62,72,107', 'W move 72, reply 107, PR #28'),
    ('16,26,56,62,97', 'W move 56, reply 97, PR #28'),
    ('16,26,62,66,263', 'W move 66, reply 263, PR #28'),
    ('16,26,62,98', 'W: every Quiet End obligation covered, PR #28'),
)


def cpu():
    """CPU seconds of this process and of every child it has reaped."""
    return sum(os.times()[:4])


def key(generators):
    return ','.join(map(str, generators))


def load_book(max_move):
    """Canonical key -> 'P'/'N': the 305,011-row exact cache (1 = P) plus
    THEORY and Hutchings primes, which must agree with it."""
    book = {}
    for line in CACHE.read_text().splitlines():
        k, bit = line.split()
        book[k] = {'1': 'P', '0': 'N'}[bit]
    sieve = bytearray([1]) * (max_move + 1)
    for n in range(2, int(max_move ** .5) + 1):
        if sieve[n]:
            sieve[n * n::n] = bytes(len(range(n * n, max_move + 1, n)))
    facts = [str(p) for p in range(5, max_move + 1) if sieve[p]] + [k for k, _ in THEORY]
    for k in facts:
        if key(minimal_generators(map(int, k.split(',')))) != k:
            raise ValueError(f'noncanonical book key {k}')
        if book.setdefault(k, 'P') != 'P':
            raise ValueError(f'book conflict at {k}')
    return book


class Player:
    """One game's player; ``choose`` returns a legal move of at least 2 and
    may set ``last_claim`` to 'win', 'loss' or 'unknown'."""
    def __init__(self, seed=0, options=None):
        self.seed, self.options = seed, dict(options or {})
        self.rng = random.Random(seed)
        self.last_claim = None

    def setup(self, hello):
        pass

    def choose(self, position, request):
        raise NotImplementedError


class RandomPlayer(Player):
    def choose(self, position, request):
        return self.rng.choice(position.legal_moves())


class SmallestPlayer(Player):
    def choose(self, position, request):
        return position.legal_moves()[0]


class ExactPlayer(Player):
    """Exact play where the solver finishes within budget, else a witness search.

    Options: ``binary`` (native solver path), ``exact_bound`` (largest Frobenius
    number attempted: 180 with the binary, 60 with the Python reference),
    ``time_share`` of the remaining clock per move (0.25) and ``memory_mb``
    per native solve (2048). Only positions whose Frobenius number is also at
    most max_move are solved, since capped play is exact there.
    """
    def __init__(self, seed=0, options=None):
        super().__init__(seed, options)
        self.binary = self.options.get('binary')
        self.bound = self.options.get('exact_bound', 180 if self.binary else 60)
        self.share = self.options.get('time_share', .25)
        self.memory_mb = self.options.get('memory_mb', 2048)
        self.known, self.deadline = {}, 0.

    def opening(self, position):
        return None

    def choose(self, position, request):
        left = request['clock']['cpu_remaining']
        self.deadline = cpu() + min(left * self.share, left - .25)
        self.last_claim = None
        move = self.opening(position)
        if move is not None:
            return move
        bound = min(self.bound, position.max_move)
        if position.gcd() == 1 and position.frobenius() <= bound:
            result = self.solve(position.generators)
            if result and result[0] == 'N' and position.is_legal(result[1]) and result[1] != 1:
                self.last_claim = 'win'
                return result[1]
            if result and result[0] == 'P':
                self.last_claim = 'loss'
                return self.complicate(position)
        move = self.witness(position, bound)
        if move is not None:
            self.last_claim = 'win'
            return move
        self.last_claim = 'unknown'
        return self.complicate(position)

    def solve(self, generators):
        """('P', None) or ('N', winning move), memoised; None if unknown in budget."""
        k = key(generators)
        if k not in self.known:
            left = self.deadline - cpu()
            if left <= 0:
                return None
            if self.binary:
                try:
                    out = subprocess.run([self.binary, *map(str, generators)], capture_output=True,
                                         text=True, timeout=left, preexec_fn=self._limit)
                except (subprocess.SubprocessError, OSError):
                    return None
                match = NATIVE.fullmatch(out.stdout.strip())
                if out.returncode or not match:
                    return None
                self.known[k] = (match[1], None if match[2] == 'none' else int(match[2]))
            else:
                s = solve_position(generators)
                self.known[k] = ('N', s.winning_move) if s.is_winning else ('P', None)
        return self.known[k]

    def _limit(self):
        size = int(self.memory_mb * 1024 ** 2)
        resource.setrlimit(resource.RLIMIT_AS, (size, size))

    def witness(self, position, bound):
        """First P child with Frobenius <= bound, in increasing (Frobenius, move)
        order. A minimal generator m of a semigroup with multiplicity e has
        m - e outside it, so such a child needs m <= bound + min(generators);
        its Frobenius number is at most bound iff it contains bound+1..bound+e."""
        gens = position.generators
        if not gens:
            return None
        limit = bound + gens[0]
        base = 1
        for g in gens:
            base = _adjoin(base, g, limit)
        candidates = []
        for m in position.legal_moves():
            if m > limit:
                break
            bits, run = _adjoin(base, m, limit), (1 << min(gens[0], m)) - 1
            if bits >> (bound + 1) & run == run:
                candidates.append(((~bits & ((1 << (bound + 1)) - 1)).bit_length() - 1, m))
        for _, m in sorted(candidates):
            if cpu() >= self.deadline:
                break
            result = self.solve(minimal_generators(gens + (m,)))
            if result and result[0] == 'P':
                return m
        return None

    def complicate(self, position):
        """Of up to 16 seeded samples and the largest legal move, the move whose
        child is infinite, else has the largest Frobenius number."""
        moves = position.legal_moves()
        sample = sorted(set(self.rng.sample(moves, min(16, len(moves)))) | {moves[-1]})

        def rank(m):
            child = position.play(m)
            return (child.gcd() != 1, child.frobenius() or 0, m)
        return max(sample, key=rank)


class BookPlayer(ExactPlayer):
    """``exact`` preceded by the outcome book: the smallest legal move to a
    known P child is played at once (from the empty position, 5)."""
    book = None

    def setup(self, hello):
        self.book = load_book(hello['rules']['max_move'])
        self.top = max(int(k.rsplit(',', 1)[-1]) for k in self.book)

    def opening(self, position):
        if self.book is None:
            self.setup({'rules': {'max_move': position.max_move}})
        for m in position.legal_moves():
            if m > self.top:
                break
            if self.book.get(key(minimal_generators(position.generators + (m,)))) == 'P':
                self.last_claim = 'win'
                return m
        return None


PLAYERS = {'random': RandomPlayer, 'smallest': SmallestPlayer, 'exact': ExactPlayer, 'book': BookPlayer}


def builtin_command(name, seed=0, options=None):
    return [sys.executable, '-m', 'sylver.arena.players', name, '--seed', str(seed),
            '--options', json.dumps(options or {}, sort_keys=True)]


def extend(position, message):
    """The requested position, replaying only the moves named since ``position``."""
    start, history, cap = message['start'], message['history'], message['rules']['max_move']
    done = len(position.history) if position else 0
    if (position is None or position.max_move != cap or list(position.start) != start
            or list(position.history) != history[:done]):
        return Position(start, history, cap)
    for move in history[done:]:
        position = position.play(move)
    return position


def main(argv=None):
    parser = argparse.ArgumentParser(description='Play one game as a built-in player over the game protocol.')
    parser.add_argument('name', choices=sorted(PLAYERS))
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--options', type=json.loads, default={})
    args = parser.parse_args(argv)
    player, position = PLAYERS[args.name](seed=args.seed, options=args.options), None
    for line in sys.stdin:
        message = json.loads(line)
        if message['type'] == 'hello':
            player.setup(message)
            reply = {'type': 'ready', 'name': args.name, 'version': VERSION}
        elif message['type'] == 'move':
            position = extend(position, message)
            player.last_claim = None
            reply = {'move': player.choose(position, message)}
            if player.last_claim:
                reply['claim'] = player.last_claim
        else:
            return 0
        print(json.dumps(reply), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
