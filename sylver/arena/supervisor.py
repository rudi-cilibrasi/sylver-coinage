"""Linux subreaper: account for and bound a complete local process tree.

wait4's rusage includes descendants already reaped by each child. Orphans are
adopted and reaped here, including grandchildren that create new sessions.
/proc sampling enforces aggregate CPU and RSS; final CPU comes from wait4,
not samples or wall time. Supervisor CPU is also charged.
"""
import ctypes
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

from .common import read, write


def descendants(root):
    records = {}
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            value = path.read_text()
            fields = value[value.rindex(')')+2:].split()
            records[int(path.parent.name)] = (int(fields[1]),
                sum(int(fields[i]) for i in (11,12,13,14)) / os.sysconf('SC_CLK_TCK'),
                int(fields[21]) * os.sysconf('SC_PAGE_SIZE'))
        except (OSError, ValueError, IndexError):
            continue
    found = {root}
    while True:
        more = {pid for pid,(ppid,_,_) in records.items() if ppid in found}
        if more <= found:
            break
        found |= more
    return {pid:records[pid] for pid in found if pid != root and pid in records}


def supervise(command, output, limits, cwd=None, env=None):
    if sys.platform != 'linux':
        raise RuntimeError('rated process-tree accounting requires Linux')
    for name in ('cpu_seconds','wall_seconds','memory_mb'):
        if isinstance(limits[name],bool) or not math.isfinite(limits[name]) or limits[name] <= 0:
            raise ValueError('invalid resource limit')
    if ctypes.CDLL(None, use_errno=True).prctl(36,1,0,0,0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'cannot become subreaper')
    output=Path(output);output.mkdir()
    cpu_start=time.process_time();start=time.monotonic()
    def cap():
        resource.setrlimit(resource.RLIMIT_AS,(int(limits['memory_mb']*1024**2),)*2)
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        # Aggregate enforcement is below; this is a second, per-process guard.
        resource.setrlimit(resource.RLIMIT_CPU,(math.ceil(limits['cpu_seconds'])+1,)*2)
    with (output/'stdout.txt').open('wb') as stdout, (output/'stderr.txt').open('wb') as stderr:
        worker=subprocess.Popen(command,stdout=stdout,stderr=stderr,cwd=cwd,env=env,
                                start_new_session=True,preexec_fn=cap)
        reaped=[];user=system=0.;reason=None;root_exit=None;peak=0;error=None
        try:
            while True:
                while True:
                    try:
                        pid,status,usage=os.wait4(-1,os.WNOHANG)
                    except ChildProcessError:
                        pid=0
                    if pid==0:
                        break
                    code=os.waitstatus_to_exitcode(status)
                    user+=usage.ru_utime;system+=usage.ru_stime
                    reaped.append({'pid':pid,'returncode':code,'user_cpu':usage.ru_utime,'system_cpu':usage.ru_stime})
                    if pid==worker.pid:
                        root_exit=code;worker.returncode=code
                active=descendants(os.getpid())
                peak=max(peak,sum(v[2] for v in active.values()))
                elapsed=time.monotonic()-start
                cpu=user+system+sum(v[1] for v in active.values())+time.process_time()-cpu_start
                if reason is None:
                    if cpu > limits['cpu_seconds']: reason='cpu-limit'
                    elif elapsed > limits['wall_seconds']: reason='wall-limit'
                    elif peak > limits['memory_mb']*1024**2: reason='memory-limit'
                    elif root_exit is not None and active: reason='orphaned-descendants'
                if reason:
                    for pid in active:
                        try: os.kill(pid,signal.SIGKILL)
                        except ProcessLookupError: pass
                if root_exit is not None and not active:
                    break
                time.sleep(.01)
        except BaseException as exc:
            error=type(exc).__name__+': '+str(exc)
            # Cancellation cannot leave solver/model descendants running.
            while True:
                active=descendants(os.getpid())
                for pid in active:
                    try: os.kill(pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                try:
                    pid,status,usage=os.wait4(-1,0)
                    user+=usage.ru_utime;system+=usage.ru_stime
                except ChildProcessError:
                    break
            reason='cancelled' if isinstance(exc,KeyboardInterrupt) else 'accounting-error'
            root_exit=-signal.SIGKILL
        supervisor_cpu=time.process_time()-cpu_start
        total=user+system+supervisor_cpu
        if total>limits['cpu_seconds'] and reason is None:reason='cpu-limit'
        report={'schema':1,'returncode':root_exit,'reason':reason,
                'cpu_seconds':total,'user_cpu':user,'system_cpu':system,
                'supervisor_cpu':supervisor_cpu,'wall_seconds':time.monotonic()-start,
                'peak_tree_rss_bytes':peak,'reaped':reaped,'limits':limits,'error':error}
        write(output/'usage.json',report)
        return report


def main():
    config=read(sys.argv[1])
    # SIGTERM/INT preserve costs and kill descendants; SIGKILL is detected as
    # missing usage by the episode controller and can never yield a score.
    def cancel(sig,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
    supervise(config['command'],config['output'],config['limits'],config.get('cwd'),config.get('env'))


if __name__=='__main__':main()
