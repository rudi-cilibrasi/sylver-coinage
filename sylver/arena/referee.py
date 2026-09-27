"""One refereed game between two untrusted player processes.

Players speak JSON Lines (schema 1) on stdin/stdout, each in a fresh session.
A player's clock is charged all CPU of the live processes in its session,
including children they have reaped, since its previous measurement: work
done after replying, even during the opponent's turn, is charged at its next
measurement. A process that leaves the session (setsid) is neither charged
nor killed. Setup (start-up and the hello/ready handshake) is capped
separately and is not charged to the clock. Every player failure is an
attributed loss; an exception in the referee itself voids the game.
"""
import json
import math
import os
from pathlib import Path
import reprlib
import resource
import select
import signal
import subprocess
import threading
import time
import traceback

from .common import sha, write
from .game import Position

CLOCK = {'cpu_base': 2.0, 'cpu_increment': 0.1, 'setup_cpu': 10.0, 'setup_wall': 60.0}
SEATS = ('first', 'second')
OTHER = {'first': 'second', 'second': 'first'}
STDERR_TAIL = 1 << 16


def session_cpu(sid, outside):
    """CPU seconds of live processes in session ``sid``, including reaped children."""
    ticks = os.sysconf('SC_CLK_TCK'); total = 0.0; members = []
    for name in os.listdir('/proc'):
        if not name.isdigit() or int(name) in outside:
            continue
        try:
            raw = Path('/proc', name, 'stat').read_bytes()
            f = raw[raw.rindex(b')') + 2:].split()
            if int(f[3]) != sid:
                outside.add(int(name)); continue
            total += sum(int(f[i]) for i in (11, 12, 13, 14)) / ticks
        except (OSError, ValueError, IndexError):
            continue
        members.append(int(name))
    return total, members


class Channel:
    """JSON Lines over a pipe with a wall-clock deadline per message."""
    def __init__(self, proc):
        self.proc, self.buffer = proc, b''
    def send(self, message):
        self.proc.stdin.write(json.dumps(message, sort_keys=True).encode() + b'\n')
        self.proc.stdin.flush()
    def receive(self, seconds, check=lambda: None):
        """``check`` runs about every 50 ms while waiting; it raises to stop
        waiting early (the referee uses it to enforce the CPU clock)."""
        deadline = time.monotonic() + seconds; fd = self.proc.stdout.fileno()
        while b'\n' not in self.buffer:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError('no reply before the wall-time limit')
            if not select.select([fd], [], [], min(left, .05))[0]:
                check()
                continue
            chunk = os.read(fd, 65536)
            if not chunk:
                raise EOFError('player closed its output')
            self.buffer += chunk
            if len(self.buffer) > 1 << 20:
                raise ValueError('oversized reply')
        line, self.buffer = self.buffer.split(b'\n', 1)
        return json.loads(line)


class Lost(Exception):
    """The player being served loses for ``reason``."""
    def __init__(self, reason, detail=''):
        super().__init__(reason)
        self.reason, self.detail = reason, str(detail)[:500]


class OutOfTime(Exception):
    """Raised while waiting, once the player's CPU exceeds what it has left."""


class Seat:
    """One player process: its session, clock, and the tail of its stderr."""
    def __init__(self, name, player, clock, max_move):
        self.name, self.player, self.proc = name, player, None
        self.remaining, self.last, self.total = clock['cpu_base'], 0.0, 0.0
        self.outside, self.tail = set(), b''
        self.setup = {'cpu': 0.0, 'wall': 0.0, 'ready': None}
        # A per-process backstop above any CPU a player can use without losing
        # on time; it only matters if this referee dies mid-game.
        self.backstop = math.ceil(clock['setup_cpu'] + clock['cpu_base'] + clock['cpu_increment'] * max_move) + 10

    def launch(self, hello, clock):
        """Start the player and complete the handshake; setup CPU is capped
        separately, and the game clock starts from the CPU used by ready."""
        start = time.monotonic()
        try:
            self.proc = subprocess.Popen([str(c) for c in self.player['command']], stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.player.get('cwd'),
                                         env=self.player.get('env'), start_new_session=True)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            raise Lost('setup-failed', error)
        self.channel = Channel(self.proc)
        self.drain = threading.Thread(target=self._drain, daemon=True)
        self.drain.start()
        # Limits are set from outside (prlimit), not in preexec_fn, which is
        # unsafe once the other seat's stderr thread is running.
        memory = int(self.player.get('memory_mb', 4096)) << 20
        for limit, value in ((resource.RLIMIT_AS, memory), (resource.RLIMIT_CORE, 0), (resource.RLIMIT_CPU, self.backstop)):
            try:
                resource.prlimit(self.proc.pid, limit, (value, value))
            except OSError:
                pass
        # A player that stops reading its input cannot block the referee: a
        # full pipe raises BlockingIOError, which is an attributed crash.
        os.set_blocking(self.proc.stdin.fileno(), False)
        failure = None

        def check():
            if self.cpu() > clock['setup_cpu']:
                raise OutOfTime
            self.alive()
        try:
            self.channel.send(hello)
            ready = self.channel.receive(clock['setup_wall'] - (time.monotonic() - start), check)
            if not isinstance(ready, dict) or ready.get('type') != 'ready':
                failure = Lost('setup-failed', 'expected a ready message')
            else:
                self.setup['ready'] = {k: str(ready[k])[:100] for k in ('name', 'version') if k in ready}
        except OutOfTime:
            pass
        except TimeoutError:
            failure = Lost('setup-failed', f"no ready message within {clock['setup_wall']} s")
        except (EOFError, OSError, ValueError, RecursionError) as error:
            failure = Lost('setup-failed', error)
        self.last = self.cpu()
        self.setup.update(cpu=round(self.last, 6), wall=round(time.monotonic() - start, 6))
        if self.last > clock['setup_cpu']:
            raise Lost('setup-cpu', f'{self.last:.3f} s of setup CPU')
        if failure:
            raise failure

    def _drain(self):
        fd = self.proc.stderr.fileno()
        while True:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                return
            if not chunk:
                return
            self.tail = (self.tail + chunk)[-STDERR_TAIL:]

    def cpu(self):
        return session_cpu(self.proc.pid, self.outside)[0]

    def alive(self):
        """Raise EOFError once the player has exited, even if a child still
        holds its stdout. WNOWAIT leaves it unreaped, so its pid keeps naming
        the session and process group that close() kills."""
        if os.waitid(os.P_PID, self.proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None:
            raise EOFError('player exited')

    def charge(self):
        """Charge all CPU since the previous measurement (never a credit)."""
        now = self.cpu()
        used, self.last = max(0.0, now - self.last), now
        self.remaining -= used
        self.total += used
        return used

    def move(self, request, position, clock):
        """One turn under the clock rule: CPU is checked before the reply."""
        start, before, failure, reply, late = time.monotonic(), self.remaining, None, None, False

        def check():
            if self.cpu() - self.last > self.remaining:
                raise OutOfTime
            self.alive()
        try:
            self.channel.send(request)
            reply = self.channel.receive(3 * before + 5, check)
        except OutOfTime:
            late = True
        except TimeoutError:
            failure = Lost('wall-time', f'no reply within {3 * before + 5:.3f} s')
        except (EOFError, OSError) as error:
            failure = Lost('crashed', error)
        except (ValueError, RecursionError) as error:
            failure = Lost('malformed-move', error)
        wall, used = time.monotonic() - start, self.charge()
        if late or self.remaining < 0:
            raise Lost('cpu-time', f'used {used:.3f} s of CPU with {before:.3f} s left')
        if failure:
            raise failure
        move = reply.get('move') if isinstance(reply, dict) else None
        if type(move) is not int:
            raise Lost('malformed-move', f'no integer move in {reprlib.repr(reply)}')
        if move == 1:
            raise Lost('named-1', 'named 1')
        if not position.is_legal(move):
            raise Lost('illegal-move', f'{move} is not a legal move')
        self.remaining += clock['cpu_increment']
        note = reply.get('note')
        return move, {'ply': request['ply'], 'seat': self.name, 'move': move, 'cpu': round(used, 6),
                      'wall': round(wall, 6), 'claim': reply.get('claim') if reply.get('claim') in ('win', 'loss', 'unknown') else None,
                      'note': note[:200] if isinstance(note, str) else None}

    def close(self, end):
        """Send ``end``, kill the whole session, and reap the player."""
        if self.proc is None:
            return
        try:
            self.channel.send(end)
        except (OSError, ValueError):
            pass
        now, members = session_cpu(self.proc.pid, self.outside)
        self.total += max(0.0, now - self.last)
        for kill, target in [(os.killpg, self.proc.pid)] + [(os.kill, pid) for pid in members]:
            try:
                kill(target, signal.SIGKILL)
            except OSError:
                pass
        self.proc.wait()
        self.drain.join(2)
        # A reader thread still blocked on stderr means an escaped process
        # holds the pipe; its descriptor stays open rather than being reused.
        for stream in (self.proc.stdin, self.proc.stdout) + (() if self.drain.is_alive() else (self.proc.stderr,)):
            try:
                stream.close()
            except OSError:
                pass


def play_game(first, second, output, start=(), max_move=1000, clock=None, game_id='game'):
    """Play one game; return its record and write it to ``output/record.json``.

    Each player is ``{'name', 'command'}`` with optional ``cwd``, ``env`` and
    ``memory_mb`` (4096). The winner of a game reaching {2,3} is the player
    who made the last move; the reason is then 'opponent-must-name-1'.
    """
    output = Path(output)
    clock = dict(CLOCK, **(clock or {}))
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in clock.values()) or not clock['cpu_base'] > 0:
        raise ValueError('clock values must be finite, non-negative numbers with cpu_base > 0')
    initial = position = Position(start, max_move=max_move)
    output.mkdir()
    players = dict(zip(SEATS, (first, second)))
    seats = {s: Seat(s, players[s], clock, max_move) for s in SEATS}
    moves, result, current = [], None, 'first'
    try:
        try:
            for current in SEATS:
                seats[current].launch({'type': 'hello', 'schema': 1, 'rules': {'max_move': max_move},
                                       'seat': current, 'clock': clock}, clock)
            current = 'first'
            while not position.over():
                seat, other = seats[current], seats[OTHER[current]]
                request = {'type': 'move', 'schema': 1, 'game': game_id, 'start': list(initial.start),
                           'history': list(position.history), 'generators': list(position.generators),
                           'gcd': position.gcd(), 'seat': current, 'ply': len(position.history) + 1,
                           'rules': {'max_move': max_move},
                           'clock': {'cpu_remaining': seat.remaining, 'cpu_increment': clock['cpu_increment'],
                                     'opponent_cpu_remaining': other.remaining}}
                move, row = seat.move(request, position, clock)
                moves.append(row)
                position = position.play(move)
                current = OTHER[current]
            result = {'winner': OTHER[current], 'loser': current, 'reason': 'opponent-must-name-1',
                      'detail': f'{current} must name 1 in {{{position.key()}}}'}
        except Lost as lost:
            result = {'winner': OTHER[current], 'loser': current, 'reason': lost.reason, 'detail': lost.detail}
    except Exception:
        result = {'winner': None, 'loser': None, 'reason': 'void', 'detail': traceback.format_exc()[-4000:]}
    finally:
        end = {'type': 'end', 'winner': result and result['winner'], 'reason': result['reason'] if result else 'void'}
        try:
            seats['first'].close(end)
        finally:
            seats['second'].close(end)
    for s in SEATS:
        (output / f'{s}.stderr').write_bytes(seats[s].tail)
    record = {'schema': 1, 'game': game_id, 'rules': {'max_move': max_move, 'loser': 'names-1'},
              'start': list(initial.start),
              'players': {s: {'name': p['name'], 'command_sha256': sha([str(c) for c in p['command']])}
                          for s, p in players.items()},
              'clock': clock, 'setup': {s: seats[s].setup for s in SEATS}, 'moves': moves, 'result': result,
              'final': {'generators': list(position.generators), 'capped': position.capped(), 'over': position.over()},
              'cpu_totals': {s: round(seats[s].total, 6) for s in SEATS}}
    write(output / 'record.json', record)
    return record
