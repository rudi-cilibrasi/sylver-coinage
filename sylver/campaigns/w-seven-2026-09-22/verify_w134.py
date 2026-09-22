#!/usr/bin/env python3
"""Replay W's move-134 refutation with empty native and optional Python memos."""
import argparse
import hashlib
import json
from math import gcd
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from sylver.short_certificates import minimal_generators, is_generated
from sylver.solver import frobenius_number, solve_position


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=900)
    parser.add_argument('--memory-gib', type=int, default=16)
    parser.add_argument('--python', action='store_true', help='also use the independent Python solver')
    args = parser.parse_args()
    if min(args.seconds, args.memory_gib) <= 0:
        parser.error('limits must be positive')
    args.output.mkdir()  # Refuse to overwrite earlier receipts.
    certificate = HERE / 'w134-certificate.json'
    data = json.loads(certificate.read_text())
    parent = tuple(data['parent'])
    first, reply = data['opponent_move'], data['reply']
    destination = tuple(data['destination'])
    if (first < 2 or reply < 2 or is_generated(parent, first)
            or is_generated((*parent, first), reply)
            or minimal_generators((*parent, first, reply)) != destination
            or gcd(*destination) != 1 or data['destination_outcome'] != 'P'
            or frobenius_number(destination) != data['frobenius']):
        raise ValueError('invalid certificate edge or finite bound')
    source = ROOT / 'sylver/native_solver.cpp'
    words = data['frobenius'] // 64 + 1
    build = args.output / 'build'
    build.mkdir()
    binary = (build / 'native').resolve()
    subprocess.run(['g++', '-std=c++20', '-O3', '-Wall', '-Wextra', '-pedantic',
                    f'-DSYLVER_NATIVE_WORDS={words}', str(source), '-o', str(binary)], check=True)
    commands = [('native', [str(binary), *map(str, destination)])]
    if args.python:
        commands.append(('python', [sys.executable, str(Path(__file__).resolve()),
                                    '--python-worker', *map(str, destination)]))
    report = {'status': 'incomplete', 'certificate_sha256': digest(certificate),
              'verifier_sha256': digest(Path(__file__)), 'native_words': words,
              'native_source_sha256': digest(source), 'binary_sha256': digest(binary),
              'python_source_sha256': digest(ROOT / 'sylver/solver.py'),
              'position': destination, 'frobenius': data['frobenius'],
              'seconds_limit_per_solver': args.seconds, 'memory_gib': args.memory_gib,
              'structural_edges_checked': 2, 'runs': {},
              'scope': 'Fresh standalone memos, no cache or inherited outcome assumptions. '
                       'Both moves are legal and their canonical destination matches the certificate.'}

    def cap():
        resource.setrlimit(resource.RLIMIT_AS, (args.memory_gib * 1024**3,) * 2)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    for name, command in commands:
        stdout, stderr = args.output / f'{name}-stdout.txt', args.output / f'{name}-stderr.txt'
        start = time.monotonic()
        timed_out = False
        with stdout.open('w') as out, stderr.open('w') as err:
            process = subprocess.Popen(command, stdout=out, stderr=err, preexec_fn=cap)
            print('VERIFY', name, 'pid', process.pid, flush=True)
            try:
                process.wait(timeout=args.seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                process.wait()
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        row = {'command': command, 'elapsed_seconds': time.monotonic() - start,
               'returncode': process.returncode, 'timed_out': timed_out,
               'stdout_sha256': digest(stdout), 'stderr_sha256': digest(stderr)}
        if process.returncode == 0:
            if name == 'native':
                match = re.fullmatch(r'P winning_move=none frobenius=(\d+) states=(\d+)\n',
                                     stdout.read_text())
                if not match or int(match[1]) != data['frobenius']:
                    raise ValueError('native result disagrees with certificate')
                row.update(outcome='P', frobenius=int(match[1]), states=int(match[2]))
            else:
                result = json.loads(stdout.read_text())
                if (result['position'] != list(destination) or result['outcome'] != 'P'
                        or result['frobenius'] != data['frobenius']
                        or result['states'] != report['runs']['native']['states']):
                    raise ValueError('Python outcome or exact state count disagrees')
                row.update(result)
        report['runs'][name] = row
        if process.returncode != 0:
            (args.output / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
            raise SystemExit(f'{name} replay incomplete; see receipt')
        if name == commands[-1][0]:
            report['status'] = 'verified'
        (args.output / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
        print('VERIFIED', name, row['states'], 'states', round(row['elapsed_seconds'], 2),
              'seconds', flush=True)


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--python-worker':
        gs = tuple(map(int, sys.argv[2:]))
        result = solve_position(gs)
        print(json.dumps({'position': gs, 'outcome': 'N' if result.is_winning else 'P',
                          'frobenius': result.frobenius, 'states': result.states_evaluated}))
    else:
        main()
