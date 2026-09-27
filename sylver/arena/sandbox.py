"""Sandboxes for untrusted provider commands: Bubblewrap, else Landlock.

Bubblewrap needs unprivileged user namespaces. Ubuntu 24.04 restricts them
through AppArmor (``kernel.apparmor_restrict_unprivileged_userns=1``), and
there every bwrap mode fails. The Landlock backend needs no privilege: this
file, run as a script, restricts itself and then execs the provider.

Landlock backend guarantees, applied before exec and inherited by every
descendant: file contents and directory listings are readable only under
/usr, /lib, /lib64, /bin and explicitly named files; writing is possible only
in a fresh scratch directory; TCP bind/connect is denied (ABI >= 4) unless
network is requested; abstract Unix sockets and signals cannot reach
processes outside the sandbox (ABI >= 6); a seccomp filter makes socket()
fail for every family without network, for AF_UNIX always (so the provider
cannot ask a session bus or other local service to act outside the sandbox),
and denies io_uring. Weaker than bwrap in two stated ways: path existence and
metadata (stat) stay visible, and there is no private PID namespace, so
other processes' /proc entries exist but are unreadable. ptrace,
process_vm_readv/writev, and pidfd_getfd are denied by seccomp, so the
same-user evaluator cannot be inspected whatever kernel.yama.ptrace_scope is.
"""
import ctypes
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

SYSTEM_DIRS = ('/usr', '/lib', '/lib64', '/bin')
SYSTEM_FILES = ('/etc/ld.so.cache', '/etc/localtime', '/dev/urandom')
NETWORK_FILES = ('/etc/ssl', '/etc/resolv.conf', '/etc/hosts')
_CREATE_RULESET, _ADD_RULE, _RESTRICT_SELF = 444, 445, 446
_IO_URING_SETUP, _PIDFD_GETFD = 425, 438
# audit arch, socket(), and the calls that read or write another process:
# ptrace, process_vm_readv, process_vm_writev. Denying them makes the
# sandbox independent of kernel.yama.ptrace_scope, since there is no PID
# namespace and the evaluator runs as the same user.
_ARCH = {'x86_64': (0xC000003E, 41, (101, 310, 311)),
         'aarch64': (0xC00000B7, 198, (117, 270, 271))}
MIN_AUTO_LANDLOCK_ABI = 6  # signal and abstract-socket scoping
_cache = {}


def _libc():
    return ctypes.CDLL(None, use_errno=True)


def landlock_abi():
    if 'abi' not in _cache:
        value = _libc().syscall(_CREATE_RULESET, None, 0, 1)  # LANDLOCK_CREATE_RULESET_VERSION
        _cache['abi'] = max(int(value), 0)
    return _cache['abi']


def _userns_blocked(binary):
    """Ubuntu's AppArmor userns restriction defeats a non-setuid bwrap."""
    try:
        restricted = Path('/proc/sys/kernel/apparmor_restrict_unprivileged_userns').read_text().strip() == '1'
    except OSError:
        return False
    return restricted and not os.stat(binary).st_mode & 0o4000


def bwrap_works():
    if 'bwrap' not in _cache:
        works = False
        binary = shutil.which('bwrap')
        if binary and not _userns_blocked(binary):
            argv = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session',
                    '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp']
            for path in SYSTEM_DIRS:
                if Path(path).exists():
                    argv += ['--ro-bind', path, path]
            try:
                works = subprocess.run([*argv, '--', '/bin/true'], capture_output=True,
                                       timeout=20).returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                works = False
        _cache['bwrap'] = works
    return _cache['bwrap']


def backend():
    """'bwrap', 'landlock', or 'none'. SYLVER_ARENA_SANDBOX may pin a backend.

    Automatic selection uses Landlock only from ABI 6, where signals and
    abstract sockets are scoped. Pinning 'landlock' accepts any ABI and the
    weaker guarantee; the ABI is recorded in every profile either way.
    """
    forced = os.environ.get('SYLVER_ARENA_SANDBOX')
    if forced:
        if forced not in ('bwrap', 'landlock'):
            raise ValueError('SYLVER_ARENA_SANDBOX must be bwrap or landlock')
        return forced
    if bwrap_works():
        return 'bwrap'
    if landlock_abi() >= MIN_AUTO_LANDLOCK_ABI and platform.machine() in _ARCH:
        return 'landlock'
    return 'none'


def describe():
    return {'backend': backend(), 'landlock_abi': landlock_abi()}


def wrap(command, provider_files, allow_network=False, scratch=None):
    """Return argv running ``command`` sandboxed. ``scratch`` is required for
    Landlock: a fresh directory that becomes the only writable location."""
    chosen = backend()
    if chosen == 'none':
        raise ValueError('sandbox unavailable: bwrap cannot create user namespaces here '
                         '(see kernel.apparmor_restrict_unprivileged_userns) and Landlock is '
                         'not supported; refusing to run an unsandboxed provider')
    files = [Path(p).resolve() for p in provider_files]
    if chosen == 'bwrap':
        mounts = [Path(p) for p in SYSTEM_DIRS]
        argv = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session',
                '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--chdir', '/tmp']
        if allow_network:
            argv += ['--share-net']
        for path in mounts:
            if path.exists():
                argv += ['--ro-bind', str(path), str(path)]
        # Explicit provider files are mounted individually, not their directory.
        for path in files:
            if not any(path.is_relative_to(m) for m in mounts):
                argv += ['--ro-bind', str(path), str(path)]
        if allow_network:
            for name in NETWORK_FILES:
                if Path(name).exists():
                    argv += ['--ro-bind', name, name]
        return [*argv, '--', *command]
    if scratch is None:
        raise ValueError('the Landlock backend needs a fresh scratch directory')
    argv = [sys.executable, str(Path(__file__).resolve()), '--scratch', str(scratch)]
    for path in files:
        argv += ['--read', str(path)]
    if allow_network:
        argv += ['--network']
    return [*argv, '--', *command]


# ---- Landlock launcher (runs as a script, before exec of the provider) ----

def _handled_fs(abi):
    handled = (1 << 13) - 1                  # ABI 1: execute .. make_sym
    if abi >= 2: handled |= 1 << 13          # refer
    if abi >= 3: handled |= 1 << 14          # truncate
    if abi >= 5: handled |= 1 << 15          # ioctl_dev
    return handled


class _RulesetAttr(ctypes.Structure):
    _fields_ = [('handled_access_fs', ctypes.c_uint64), ('handled_access_net', ctypes.c_uint64),
                ('scoped', ctypes.c_uint64)]


class _PathBeneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]


class _Filter(ctypes.Structure):
    _fields_ = [('code', ctypes.c_uint16), ('jt', ctypes.c_uint8), ('jf', ctypes.c_uint8),
                ('k', ctypes.c_uint32)]


class _Program(ctypes.Structure):
    _fields_ = [('len', ctypes.c_ushort), ('filter', ctypes.POINTER(_Filter))]


def _check(result, what):
    if result < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, f'{what}: {os.strerror(errno)}')
    return result


def _landlock(libc, abi, read_dirs, read_files, write_dirs, allow_network):
    fs = _handled_fs(abi)
    attr = _RulesetAttr(fs, 0, 0)
    if abi >= 4 and not allow_network:
        attr.handled_access_net = 0b11       # bind_tcp | connect_tcp, no port allowed
    if abi >= 6:
        attr.scoped = 0b11                   # abstract unix sockets | signals
    ruleset = _check(libc.syscall(_CREATE_RULESET, ctypes.byref(attr), ctypes.sizeof(attr), 0),
                     'landlock_create_ruleset')
    file_rights = fs & ((1 << 0) | (1 << 1) | (1 << 2) | (1 << 14) | (1 << 15))
    execute_read = (1 << 0) | (1 << 2)

    def rule(path, rights):
        try:
            fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
        except FileNotFoundError:
            return
        try:
            if not Path(path).is_dir():
                rights &= file_rights
            beneath = _PathBeneath(rights & fs, fd)
            _check(libc.syscall(_ADD_RULE, ruleset, 1, ctypes.byref(beneath), 0), f'landlock_add_rule {path}')
        finally:
            os.close(fd)

    for path in (*read_dirs, *read_files):
        rule(path, execute_read | (1 << 3))  # read_dir is dropped for files
    rule('/dev/null', (1 << 1) | (1 << 2))
    for path in write_dirs:
        rule(path, fs)
    return ruleset


def _seccomp(libc, allow_network):
    arch, socket_nr, (ptrace, vm_read, vm_write) = _ARCH[platform.machine()]
    LD, JEQ, JGE, RET = 0x20, 0x15, 0x35, 0x06
    ALLOW, ERRNO, KILL = 0x7fff0000, 0x00050000 | 1, 0x80000000   # EPERM
    # A jump at index i goes to i+1+offset. Targets are noted per row.
    prog = [
        (LD, 0, 0, 4),                        # 0 arch
        (JEQ, 0, 13, arch),                   # 1 foreign arch -> 15 kill
        (LD, 0, 0, 0),                        # 2 syscall number
        (JGE, 10, 0, 0x40000000),             # 3 x32 ABI -> 14 errno
        (JEQ, 9, 0, _IO_URING_SETUP),         # 4 -> 14 errno
        (JEQ, 8, 0, ptrace),                  # 5 -> 14 errno
        (JEQ, 7, 0, vm_read),                 # 6 -> 14 errno
        (JEQ, 6, 0, vm_write),                # 7 -> 14 errno
        (JEQ, 5, 0, _PIDFD_GETFD),            # 8 -> 14 errno
        (JEQ, 1, 0, socket_nr),               # 9 -> 11 family check
        (RET, 0, 0, ALLOW),                   # 10
        (LD, 0, 0, 16),                       # 11 socket family (args[0] low word)
        (JEQ, 1, 0, 1),                       # 12 AF_UNIX -> 14 errno
        (RET, 0, 0, ALLOW if allow_network else ERRNO),  # 13 other families
        (RET, 0, 0, ERRNO),                   # 14
        (RET, 0, 0, KILL),                    # 15
    ]
    array = (_Filter * len(prog))(*[_Filter(*row) for row in prog])
    program = _Program(len(prog), array)
    _check(libc.prctl(22, 2, ctypes.byref(program), 0, 0), 'seccomp')   # PR_SET_SECCOMP, FILTER


def _launch(argv):
    import argparse
    parser = argparse.ArgumentParser(description='Landlock provider launcher')
    parser.add_argument('--scratch', required=True)
    parser.add_argument('--read', action='append', default=[])
    parser.add_argument('--network', action='store_true')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('missing provider command')
    libc = _libc()
    abi = landlock_abi()
    if abi < 1 or platform.machine() not in _ARCH:
        raise SystemExit('landlock sandbox unavailable on this kernel/architecture')
    try:
        os.setsid()                          # no controlling terminal to inject into
    except PermissionError:
        pass                                 # already a session leader
    _check(libc.prctl(1, 9, 0, 0, 0), 'PR_SET_PDEATHSIG')          # SIGKILL with the parent
    _check(libc.prctl(38, 1, 0, 0, 0), 'PR_SET_NO_NEW_PRIVS')
    read_files = [*SYSTEM_FILES, *args.read, *(NETWORK_FILES if args.network else ())]
    ruleset = _landlock(libc, abi, SYSTEM_DIRS, read_files, [args.scratch], args.network)
    _seccomp(libc, args.network)
    _check(libc.syscall(_RESTRICT_SELF, ruleset, 0), 'landlock_restrict_self')
    os.close(ruleset)
    os.chdir(args.scratch)
    env = dict(os.environ, TMPDIR=args.scratch, HOME=args.scratch)
    os.execve(command[0], command, env)


if __name__ == '__main__':
    _launch(sys.argv[1:])
