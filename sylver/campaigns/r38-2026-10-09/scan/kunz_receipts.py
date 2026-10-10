"""Sequential kunz_solver replays of B56's largest finite witnesses (100 million states and more).

These destinations get a native_solver.cpp replay (verify_finite_reply, without
--python) and this second, independent replay: kunz_solver.cpp from main,
--threads 1 (the state count native_solver.cpp reports), --verify-memo with its
scalar reference moves. Usage: kunz_receipts.py MOVE... (B56's obligations).
Writes r38/verification/b56_<m>/kunz-{stdout,stderr}.txt and kunz-receipt.json,
and keeps the exact source in r38/verification/sources/.
"""
import hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/ruclaw/src/sylver-coinage')
sys.path.insert(0, str(ROOT))
from sylver.arena.common import position  # noqa: E402

B56 = (16, 38, 56, 60)
BUILD = ['g++', '-std=c++20', '-O3', '-Wall', '-Wextra', '-pedantic', '-Werror', '-pthread', '-march=native']


def main(moves):
    commit = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                            check=True).stdout.strip()
    sources = HERE / 'r38/verification/sources'
    sources.mkdir(parents=True, exist_ok=True)
    source = sources / f'kunz_solver-{commit[:7]}.cpp'
    binary = HERE / f'kunz-{commit[:7]}'
    if not (source.exists() and binary.exists()
            and source.read_bytes() == (ROOT / 'sylver/kunz_solver.cpp').read_bytes()):
        # Build once; a second concurrent instance reuses the binary instead of rewriting it.
        source.write_bytes((ROOT / 'sylver/kunz_solver.cpp').read_bytes())
        subprocess.run([*BUILD, str(source), '-o', str(binary)], check=True)
    for m in moves:
        cert = json.loads((HERE / f'r38/b56_{m}-certificate.json').read_text())
        dest = position((*B56, m, cert['reply']))
        assert list(dest) == cert['destination']
        out = HERE / f'r38/verification/b56_{m}'
        args = ['--threads', '1', '--verify-memo', '--verify-threads', '6', '--memo-stats', *map(str, dest)]
        proc = subprocess.run(['/usr/bin/time', '-v', str(binary), *args], capture_output=True, text=True)
        (out / 'kunz-stdout.txt').write_text(proc.stdout)
        (out / 'kunz-stderr.txt').write_text(proc.stderr)
        elapsed = re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (?:(\d+):)?(\d+):([\d.]+)', proc.stderr)
        rss = re.search(r'Maximum resident set size \(kbytes\): (\d+)', proc.stderr)
        first = proc.stdout.splitlines()[0].split()
        receipt = {'position': list(dest), 'frobenius': cert['frobenius'], 'source': 'sylver/kunz_solver.cpp',
                   'commit': commit, 'source_snapshot': f'../sources/{source.name}',
                   'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'build': ' '.join(BUILD),
                   'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                   'command': [binary.name, *args], 'returncode': proc.returncode,
                   'elapsed_seconds': (int(elapsed.group(1) or 0) * 3600 + int(elapsed.group(2)) * 60
                                       + float(elapsed.group(3))) if elapsed else None,
                   'max_rss_kib': int(rss.group(1)) if rss else None,
                   'stdout_sha256': hashlib.sha256(proc.stdout.encode()).hexdigest(),
                   'stderr_sha256': hashlib.sha256(proc.stderr.encode()).hexdigest(),
                   'outcome': first[0], 'states': int(first[3].split('=')[1])}
        (out / 'kunz-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(m, receipt['outcome'], receipt['states'], receipt['elapsed_seconds'], receipt['returncode'], flush=True)


if __name__ == '__main__':
    main([int(x) for x in sys.argv[1:]])
