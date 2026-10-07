"""One refereed game between two player processes.

Players speak JSON Lines (schema 1) on stdin/stdout, each in a fresh session
and, where cgroup v2 is delegated to this user, in its own child cgroup of
the referee's. A player's clock is charged all CPU used by what it started
since its previous measurement, so work done after replying, even during
the opponent's turn, is charged at its next measurement. With a cgroup that
is the cumulative cpu.stat usage, which keeps the CPU of every descendant
however it exits, and cgroup.kill ends them all. The fallback sums /proc
over the live members of the session, including children they reaped; it
misses children reaped by no member (SIGCHLD ignored, orphans reaped by
init) and processes that leave the session, which it cannot kill either.
Players are not isolated from each other or from this referee: run only
trusted programs. Setup (start-up and the hello/ready handshake) is capped
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
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import traceback

from . import sandbox
from .common import canonical, sha, write
from .game import Position

CLOCK = {'cpu_base': 2.0, 'cpu_increment': 0.1, 'setup_cpu': 10.0, 'setup_wall': 60.0}
SEATS = ('first', 'second')
OTHER = {'first': 'second', 'second': 'first'}
STDERR_TAIL = 1 << 16
CGROUPS = Path('/sys/fs/cgroup')
# /bin/sh -c ENTER CGROUP COMMAND...: the shell moves itself into CGROUP and
# execs the player, so all its descendants start there. If the move fails the
# player still runs, and the referee finds it outside and falls back to /proc.
ENTER = 'echo $$ > "$0/cgroup.procs" 2>/dev/null; exec "$@"'


def game_clock(clock=None):
    """CLOCK updated by ``clock``: known keys only, finite non-negative
    numbers (not booleans), and a positive cpu_base."""
    clock = dict(CLOCK, **(clock or {}))
    if (set(clock) != set(CLOCK) or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
                                        for v in clock.values()) or not clock['cpu_base'] > 0):
        raise ValueError(f'invalid clock {clock}: keys {sorted(CLOCK)}, finite non-negative numbers, cpu_base > 0')
    return clock


def remove_cgroup(path):
    """Kill everything in cgroup ``path`` and below, then remove those
    cgroups; killed processes may take a moment to leave them."""
    try:
        (path / 'cgroup.kill').write_text('1')
    except OSError:
        pass
    deadline = time.monotonic() + 5

    def remove(directory):
        for child in [c for c in directory.iterdir() if c.is_dir()]:
            remove(child)
        while True:
            try:
                directory.rmdir()
                return
            except FileNotFoundError:
                return
            except OSError:
                if time.monotonic() > deadline:
                    return
                time.sleep(.01)
    try:
        remove(path)
    except OSError:
        pass


def own_cgroup():
    """This process's cgroup v2 directory, if this user may create children
    in it and move processes between them; else None."""
    try:
        line = next(x for x in Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0::'))
    except (OSError, StopIteration):
        return None
    path = CGROUPS / line[3:].lstrip('/')
    return path if os.access(path, os.W_OK) and os.access(path / 'cgroup.procs', os.W_OK) else None


def text(value, limit):
    """Player-supplied text as valid UTF-8, truncated: json.loads accepts lone
    surrogates such as \\ud800, which cannot be encoded, so they become '?'."""
    value = value if isinstance(value, str) else reprlib.repr(value)
    return value.encode('utf-8', 'replace').decode('utf-8')[:limit]


def clean(value):
    """A copy that canonical JSON accepts: valid UTF-8 text, finite numbers."""
    if isinstance(value, str):
        return value.encode('utf-8', 'replace').decode('utf-8')
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {clean(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def session_cpu(sid, outside):
    """CPU seconds of the processes in session ``sid``, including reaped
    children, and the pids of its members that are not zombies.

    ``outside`` caches pids known to be in other sessions; pids that have
    left /proc are dropped from it on every scan, so a reused pid is
    classified afresh unless it was reused within one scan gap."""
    ticks = os.sysconf('SC_CLK_TCK'); total = 0.0; members = []
    present = {int(n) for n in os.listdir('/proc') if n.isdigit()}
    outside.intersection_update(present)
    for pid in present - outside:
        try:
            raw = Path('/proc', str(pid), 'stat').read_bytes()
            f = raw[raw.rindex(b')') + 2:].split()
            if int(f[3]) != sid:
                outside.add(pid); continue
            total += sum(int(f[i]) for i in (11, 12, 13, 14)) / ticks
        except (OSError, ValueError, IndexError):
            continue
        if f[0] != b'Z':
            members.append(pid)
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
        waiting early (the referee uses it to enforce the CPU clock). poll(),
        unlike select(), accepts descriptors above 1023."""
        deadline = time.monotonic() + seconds; fd = self.proc.stdout.fileno()
        poller = select.poll(); poller.register(fd, select.POLLIN)
        while b'\n' not in self.buffer:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError('no reply before the wall-time limit')
            if not poller.poll(math.ceil(min(left, .05) * 1000)):
                check()
                continue
            chunk = os.read(fd, 65536)
            if not chunk:
                raise EOFError('player closed its output')
            self.buffer += chunk
            if len(self.buffer) > 1 << 20:
                raise ValueError('oversized reply')
        line, self.buffer = self.buffer.split(b'\n', 1)
        # Decode as UTF-8 first (as json.loads would for UTF-8, a leading
        # byte-order mark included): given bytes, json.loads also accepts
        # UTF-16 and UTF-32, whose brackets a check of the text would not
        # see. A str skips that detection.
        reply = line.decode('utf-8-sig', 'surrogatepass')
        if nested_too_deeply(reply):
            raise ValueError('reply nested too deeply')
        return json.loads(reply)


MAX_REPLY_DEPTH = 32   # a reply is one flat object; anything deeper is malformed


def nested_too_deeply(text, limit=MAX_REPLY_DEPTH):
    """True when JSON brackets in ``text`` (a str) nest deeper than ``limit``.

    json.loads recurses once per level and relies on the interpreter's
    recursion limit to stop: in a process that raised it (sylver.periodicity
    sets 100,000 on import), a hostile reply such as 100,000 '[' would
    exhaust the C stack and crash the referee instead of losing the game.
    Strings are skipped, so brackets inside them do not count; past an
    unterminated string json.loads fails before recursing.
    """
    if text.count('[') + text.count('{') <= limit:
        return False
    depth, in_string, escaped = 0, False, False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in '[{':
            depth += 1
            if depth > limit:
                return True
        elif char in ']}':
            depth -= 1
    return False


class Lost(Exception):
    """The player being served loses for ``reason``."""
    def __init__(self, reason, detail=''):
        super().__init__(reason)
        self.reason, self.detail = reason, text(str(detail), 500)


class OutOfTime(Exception):
    """Raised while waiting, once the player's CPU exceeds what it has left."""


class Seat:
    """One player process: its cgroup or session, clock, and stderr tail."""
    def __init__(self, name, player, clock, max_move, cgroups=None):
        self.name, self.player, self.proc, self.cgroups, self.cgroup = name, player, None, cgroups, None
        self.scratch = None
        self.accounting = 'session'
        self.remaining, self.last, self.total = clock['cpu_base'], 0.0, 0.0
        self.outside, self.tail, self.stopping = set(), b'', False
        self.setup = {'cpu': 0.0, 'wall': 0.0, 'ready': None}
        # A per-process backstop above any CPU a player can use without losing
        # on time; it only matters if this referee dies mid-game.
        self.backstop = math.ceil(clock['setup_cpu'] + clock['cpu_base'] + clock['cpu_increment'] * max_move) + 10

    def launch(self, hello, clock):
        """Start the player and complete the handshake; setup CPU is capped
        separately, and the game clock starts from the CPU used by ready."""
        start, command = time.monotonic(), [str(c) for c in self.player['command']]
        box = self.player.get('sandbox')
        if box is not None:
            # Inside the cgroup wrapper, so the move into the cgroup happens
            # before the sandbox closes the filesystem. A missing backend is
            # the referee's failure, never the player's loss.
            self.scratch = tempfile.mkdtemp(prefix='sylver-player-')
            command = sandbox.wrap(command, [str(x) for x in box.get('read', ())], bool(box.get('network')), self.scratch)
            self.setup['sandbox'] = sandbox.backend()
        if self.cgroups is not None:
            cgroup = self.cgroups / f'sylver-game-{os.getpid()}-{time.monotonic_ns()}-{self.name}'
            try:
                cgroup.mkdir()
                self.cgroup, self.accounting, command = cgroup, 'cgroup', ['/bin/sh', '-c', ENTER, str(cgroup), *command]
            except OSError:
                pass
        try:
            self.proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         cwd=self.player.get('cwd'), env=self.player.get('env'), start_new_session=True)
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
                self.setup['ready'] = {k: text(ready[k], 100) for k in ('name', 'version') if k in ready}
        except OutOfTime:
            failure = Lost('setup-cpu', f"over {clock['setup_cpu']} s of setup CPU before ready")
        except TimeoutError:
            failure = Lost('setup-failed', f"no ready message within {clock['setup_wall']} s")
        except (EOFError, OSError, ValueError, RecursionError) as error:
            failure = Lost('setup-failed', error)
        if failure is None and self.cgroup is not None and str(self.proc.pid) not in self._read('cgroup.procs').split():
            self._release()           # the player is not inside: account via /proc instead
            self.accounting = 'session'
        self.last = self.cpu()
        self.setup.update(cpu=round(self.last, 6), wall=round(time.monotonic() - start, 6))
        if self.last > clock['setup_cpu']:
            raise Lost('setup-cpu', f'{self.last:.3f} s of setup CPU')
        if failure:
            raise failure

    def _drain(self):
        """Keep the last STDERR_TAIL bytes of stderr until EOF or close()."""
        fd = self.proc.stderr.fileno()
        poller = select.poll(); poller.register(fd, select.POLLIN)
        while not self.stopping:
            if not poller.poll(100):
                continue
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                return
            if not chunk:
                return
            self.tail = (self.tail + chunk)[-STDERR_TAIL:]

    def cpu(self):
        """Cumulative CPU seconds of everything the player started."""
        if self.accounting == 'cgroup':
            return int(self._read('cpu.stat').split('usage_usec ', 1)[1].split()[0]) / 1e6
        return session_cpu(self.proc.pid, self.outside)[0]

    def _read(self, name):
        return (self.cgroup / name).read_text()

    def _release(self):
        if self.cgroup is not None:
            remove_cgroup(self.cgroup)
            self.cgroup = None
        if self.scratch is not None:
            shutil.rmtree(self.scratch, ignore_errors=True)
            self.scratch = None

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
                      'note': text(note, 200) if isinstance(note, str) else None}

    def close(self, end):
        """Send ``end``, kill everything the player started, and reap it."""
        if self.proc is None:
            self._release()
            return
        try:
            self.channel.send(end)
        except (OSError, ValueError):
            pass
        if self.accounting == 'cgroup':
            try:
                (self.cgroup / 'cgroup.kill').write_text('1')
            except OSError:
                pass
        else:                         # /proc loses the CPU of processes once they die
            self.total += max(0.0, self.cpu() - self.last)
        # Then kill session members until none is alive (outside the cgroup,
        # if any): a member forking during one pass is caught by the next,
        # which rescans /proc in full.
        deadline = time.monotonic() + 10
        while True:
            self.outside.clear()
            members = session_cpu(self.proc.pid, self.outside)[1]
            for kill, target in [(os.killpg, self.proc.pid)] + [(os.kill, pid) for pid in members]:
                try:
                    kill(target, signal.SIGKILL)
                except OSError:
                    pass
            if not members or time.monotonic() > deadline:
                break
            time.sleep(.005)
        self.proc.wait()
        if self.accounting == 'cgroup':
            self.total += max(0.0, self.cpu() - self.last)
        self._release()
        # The reader stops within 0.1 s even if an escaped process still holds
        # stderr, so every pipe is closed and no descriptor can be reused under it.
        self.stopping = True
        self.drain.join(5)
        for stream in (self.proc.stdin, self.proc.stdout) + (() if self.drain.is_alive() else (self.proc.stderr,)):
            try:
                stream.close()
            except OSError:
                pass


def play_game(first, second, output, start=(), max_move=1000, clock=None, game_id='game', accounting=None,
              cgroups=None):
    """Play one game; return its record and write it to ``output/record.json``.

    Each player is ``{'name', 'command'}`` with optional ``cwd``, ``env`` and
    ``memory_mb`` (4096). The winner of a game reaching {2,3} is the player
    who made the last move; the reason is then 'opponent-must-name-1'.
    ``accounting`` is 'cgroup', 'session', or None for cgroup where possible;
    the record says which each seat used. Seat cgroups are made under
    ``cgroups``, by default this process's own cgroup.
    """
    output, clock = Path(output), game_clock(clock)
    initial = position = Position(start, max_move=max_move)
    players = dict(zip(SEATS, (first, second)))
    digests = {s: sha([str(c) for c in p['command']]) for s, p in players.items()}   # commands must be UTF-8
    cgroups = cgroups or own_cgroup()
    accounting = accounting or ('cgroup' if cgroups else 'session')
    if accounting not in ('cgroup', 'session') or accounting == 'cgroup' and cgroups is None:
        raise ValueError(f'unsupported CPU accounting {accounting!r} here')
    output.mkdir()
    seats = {s: Seat(s, players[s], clock, max_move, cgroups if accounting == 'cgroup' else None) for s in SEATS}
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
        result = {'winner': None, 'loser': None, 'reason': 'void', 'detail': text(traceback.format_exc()[-4000:], 4000)}
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
              'players': {s: {'name': p['name'], 'command_sha256': digests[s]} for s, p in players.items()},
              'clock': clock, 'setup': {s: seats[s].setup for s in SEATS}, 'moves': moves, 'result': result,
              'final': {'generators': list(position.generators), 'capped': position.capped(), 'over': position.over()},
              'cpu_totals': {s: round(seats[s].total, 6) for s in SEATS},
              'accounting': {s: seats[s].accounting for s in SEATS}}
    try:
        canonical(record)
    except (UnicodeError, ValueError):
        record = clean(record)        # a result is never lost to unencodable text
    write(output / 'record.json', record)
    return record
