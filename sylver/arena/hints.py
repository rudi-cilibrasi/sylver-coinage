"""Untrusted outcome hints: the frozen database as a content-addressed oracle.

A hint file is gzip(text) with one sorted line per position, ``KEY OUTCOME``,
KEY the canonical comma-separated generators and OUTCOME P or N. Its identity
is the SHA-256 of the uncompressed text, pinned by golf manifests. Hints are
never proof dependencies: no proof rule can cite them and they never enter a
session's proof nodes, so a wrong hint can only make a certificate fail the
fixed verifier's replay.
"""
import bisect
import gzip
from pathlib import Path

from .common import key, sha


def encode(rows):
    """Canonical hint text for (generators, outcome) rows; conflicts are errors."""
    table = {}
    for p, outcome in rows:
        if outcome not in ('P', 'N'):
            raise ValueError('hint outcome must be P or N')
        k = key(p)
        if table.setdefault(k, outcome) != outcome:
            raise ValueError(f'conflicting hint: {k}')
    return ''.join(f'{k} {table[k]}\n' for k in sorted(table)).encode()


def path_for(directory, digest):
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('invalid hint digest')
    return Path(directory) / 'hints' / f'{digest}.txt.gz'


def save(directory, data):
    """Store hint text once under ``directory/hints``; return its digest."""
    digest = sha(data)
    path = path_for(directory, digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix('.tmp')
        tmp.write_bytes(gzip.compress(data, mtime=0))
        tmp.replace(path)
    return digest


class Hints:
    """Read-only lookup; the file must match ``digest`` and be strictly sorted."""
    def __init__(self, path, digest):
        data = gzip.decompress(Path(path).read_bytes())
        if sha(data) != digest:
            raise ValueError('hint content mismatch')
        keys, outcomes, previous = [], [], None
        for line in data.decode().splitlines():
            k, _, outcome = line.partition(' ')
            if outcome not in ('P', 'N') or not k or (previous is not None and k <= previous):
                raise ValueError('malformed, duplicated, or unsorted hint file')
            keys.append(k)
            outcomes.append(outcome)
            previous = k
        self.keys, self.outcomes, self.digest = keys, outcomes, digest

    def __len__(self):
        return len(self.keys)

    def get(self, p):
        k = key(p)
        i = bisect.bisect_left(self.keys, k)
        return self.outcomes[i] if i < len(self.keys) and self.keys[i] == k else 'unknown'
