import gzip
from pathlib import Path
import tempfile
import unittest

from sylver.arena.book import add_certificate, admit, measure, record, render_book, verify_book
from sylver.arena.common import canonical, key, read, sha, write
from sylver.arena.episode import DEFAULT_LIMITS, execution_profile, run_episode
from sylver.arena.exact import build_tools
from sylver.arena.fixtures import make_bundle, tiny_baseline
from sylver.arena.hints import Hints, encode, path_for, save
from sylver.arena.policies import GOLF, _genus
from sylver.arena.proof import canonical_proof, verifier_profile
from sylver.arena.protocol import Client, Session
from sylver.arena.snapshot import manifest, snapshot, validate_bundle
from sylver.short_certificates import minimal_generators
from sylver.solver import FiniteSolver, frobenius_number, solve_position

LIMITS = dict(DEFAULT_LIMITS, cpu_seconds=60., wall_seconds=120., memory_mb=2048, query_wall_seconds=30.)


def outcome(p):
    return 'N' if solve_position(p).is_winning else 'P'


def family(target):
    """Target and all of its children, with reference outcomes."""
    s = FiniteSolver(target)
    rows = [(target, outcome(target))]
    for m in s.legal_moves(s.initial_state):
        c = minimal_generators(target + (m,))
        rows.append((c, outcome(c)))
    return rows


def golf_bundle(directory, target, rows):
    digest = save(directory, encode(rows))
    base = snapshot()
    m = manifest(target, base, verifier_profile(), execution_profile(LIMITS), 'golf', 'test', digest)
    return {'manifest': m, 'snapshot': base}, str(path_for(directory, digest))


class HintTests(unittest.TestCase):
    def test_encoding_is_canonical_and_conflicts_fail(self):
        a = encode([((5, 7), 'N'), ((4, 5, 11), 'P'), ((7, 5), 'N')])
        self.assertEqual(a, b'4,5,11 P\n5,7 N\n')
        with self.assertRaises(ValueError):
            encode([((5, 7), 'N'), ((5, 7), 'P')])
        with self.assertRaises(ValueError):
            encode([((5, 7), 'unknown')])

    def test_load_lookup_and_tamper(self):
        rows = family((6, 7, 11))
        with tempfile.TemporaryDirectory() as d:
            digest = save(d, encode(rows))
            h = Hints(path_for(d, digest), digest)
            for p, o in rows:
                self.assertEqual(h.get(p), o)
            self.assertEqual(h.get((4, 9)), 'unknown')
            with self.assertRaises(ValueError):
                Hints(path_for(d, digest), '0' * 64)
            bad = Path(d) / 'bad.txt.gz'
            for text in (b'5,7 N\n4,5 N\n', b'4,5 N\n4,5 N\n', b'4,5 X\n'):
                bad.write_bytes(gzip.compress(text))
                with self.assertRaises(ValueError):
                    Hints(bad, sha(text))

    def test_only_golf_manifests_pin_hints(self):
        base = snapshot()
        with self.assertRaises(ValueError):
            manifest((5, 7), base, verifier_profile(), {}, 'training', '', 'a' * 64)
        with self.assertRaises(ValueError):
            manifest((5, 7), base, verifier_profile(), {}, 'golf', '', 'not-a-digest')
        golf = {'manifest': manifest((5, 7), base, verifier_profile(), {}, 'golf', '', 'a' * 64), 'snapshot': base}
        validate_bundle(golf)
        plain = {'manifest': manifest((5, 7), base, verifier_profile(), {}, 'held-out'), 'snapshot': base}
        validate_bundle(plain)
        self.assertNotIn('hints', plain['manifest'])

    def test_hints_never_become_proof_nodes(self):
        rows = family((5, 7))
        with tempfile.TemporaryDirectory() as d:
            bundle, path = golf_bundle(d, (5, 7), rows)
            session = Session(bundle, str(build_tools(Path(d) / 'tools')), Path(d) / 'run', LIMITS, hints=path)
            client = Client(session)
            got = client.call('hint', positions=[[5, 7], [4, 9]])
            self.assertEqual(got['trust'], 'untrusted-hint')
            self.assertEqual([r['outcome'] for r in got['rows']], ['N', 'unknown'])
            with self.assertRaises(ValueError):
                client.call('proof', position=[5, 7])
            self.assertEqual(client.call('lookup', position=[5, 7])['outcome'], 'unknown')
            cite = {'schema': 1, 'root': '5,7', 'nodes': {'5,7': {'rule': 'baseline', 'outcome': 'N', 'fact': 'x' * 64}}}
            with self.assertRaises(ValueError):
                canonical_proof(cite, bundle['snapshot'], (5, 7))


class GolfEpisodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.root = Path(cls.tmp.name)
        cls.tools = cls.root / 'tools'; build_tools(cls.tools)
        cls.target = (7, 9, 11)
        cls.rows = family(cls.target)
        cls.bundle, cls.hints = golf_bundle(cls.root / 'fixture', cls.target, cls.rows)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def episode(self, name, policy, bundle=None, hints='default'):
        return run_episode(bundle or self.bundle, policy, self.root / name, self.tools,
                           hints=self.hints if hints == 'default' else hints)

    def test_strategies_produce_valid_certificates(self):
        self.assertEqual(outcome(self.target), 'N')
        receipts = {n: self.episode('s-' + n, p) for n, p in GOLF.items()}
        for name, r in receipts.items():
            self.assertEqual((r['status'], r['outcome']), ('valid', 'N'), name)
        root = read(self.root / 's-golf-root/certificate.json')
        self.assertEqual(root['nodes'], {key(self.target): {'outcome': 'N', 'rule': 'finite'}})
        witness = read(self.root / 's-golf-witness/certificate.json')
        node = witness['nodes'][key(self.target)]
        children = [(_genus(p), frobenius_number(p), p) for p, o in self.rows[1:] if o == 'P']
        self.assertEqual(node['child'], key(min(children)[2]))
        self.assertIn(read(self.root / 's-golf-probe/certificate.json')['nodes'][key(self.target)]['rule'],
                      ('finite', 'edge'))

    def test_even_target_is_answered_by_a_hinted_odd_witness(self):
        # {10,16} has gcd 2, so no finite root leaf exists; 9 answers it
        # ({9,10,16} is P), as in the certified opening-16 table.
        target = (10, 16)
        rows = [(target, 'N')] + [(minimal_generators(target + (m,)), outcome(minimal_generators(target + (m,))))
                                  for m in range(3, 40, 2)]
        bundle, path = golf_bundle(self.root / 'even', target, rows)
        for name in ('golf-root', 'golf-probe'):
            r = run_episode(bundle, GOLF[name], self.root / ('even-' + name), self.tools, hints=path)
            self.assertEqual((r['status'], r['outcome']), ('valid', 'N'), name)
            node = read(self.root / ('even-' + name) / 'certificate.json')['nodes']['10,16']
            self.assertEqual((node['rule'], node['move'], node['child']), ('edge', 9, '9,10,16'))

    def test_false_hint_cannot_score(self):
        rows = [(p, o) for p, o in self.rows if p != self.target] + [(self.target, 'P')]
        bundle, path = golf_bundle(self.root / 'false', self.target, rows)
        r = run_episode(bundle, GOLF['golf-root'], self.root / 'false-run', self.tools, hints=path)
        self.assertEqual(r['status'], 'invalid')
        self.assertIsNone(r['S'])

    def test_pinned_hint_file_is_required_and_checked(self):
        with self.assertRaises(ValueError):
            self.episode('missing', GOLF['golf-root'], hints=None)
        other = save(self.root / 'other', encode(self.rows[:3]))
        with self.assertRaises(ValueError):
            self.episode('mismatch', GOLF['golf-root'], hints=str(path_for(self.root / 'other', other)))
        plain = make_bundle([4, 5], tiny_baseline(), 'training', LIMITS)
        with self.assertRaises(ValueError):
            run_episode(plain, GOLF['golf-root'], self.root / 'plain', self.tools, hints=self.hints)

    def test_book_round_trip(self):
        r = self.episode('book-src', GOLF['golf-witness'])
        self.assertEqual(r['status'], 'valid')
        book = self.root / 'book'
        entry = add_certificate(book, self.root / 'book-src', self.tools, competitor='golf-witness', repeats=2)
        self.assertEqual(entry['certificate'], r['verification']['certificate_sha256'])
        self.assertGreater(entry['states'], 0)
        index = read(book / 'index.json')
        self.assertEqual(index['targets'][key(self.target)]['record'], entry['certificate'])
        self.assertTrue((book / 'certificates' / (entry['certificate'] + '.json')).exists())
        root_leaf = {'schema': 1, 'root': key(self.target), 'nodes': {key(self.target): {'rule': 'finite', 'outcome': 'N'}}}
        admit(book, root_leaf, measure(root_leaf, self.tools, repeats=1))
        self.assertEqual(len(read(book / 'index.json')['targets'][key(self.target)]['entries']), 2)
        self.assertTrue(all(x['ok'] for x in verify_book(book, self.tools)))
        self.assertIn(key(self.target), render_book(book))
        bad = self.episode('book-bad', GOLF['golf-root'], hints='default')
        write(self.root / 'book-bad/receipt.json', dict(read(self.root / 'book-bad/receipt.json'), status='invalid'))
        with self.assertRaises(ValueError):
            add_certificate(book, self.root / 'book-bad', self.tools)

    def test_record_is_deterministic_checking_cost(self):
        from sylver.arena.book import RATE, cost
        a = {'certificate': 'a', 'C': 133, 'states': 3_747_484}   # a root leaf
        b = {'certificate': 'b', 'C': 217, 'states': 2_657_828}   # a witness edge
        self.assertLess(cost(b), cost(a))
        self.assertEqual(record([a, b]), 'b')
        c = {'certificate': 'c', 'C': 400, 'states': 2_600_000}  # fewer states, too many bytes
        self.assertEqual(record([a, b, c]), 'b')
        self.assertEqual(cost({'C': 0, 'states': RATE}), 200)

    def test_book_refuses_mixed_verifiers_and_handles_leafless_proofs(self):
        book = self.root / 'book-mixed'
        leafless = {'schema': 1, 'root': '2,3', 'nodes': {'2,3': {'rule': 'cover', 'outcome': 'P', 'tail': 'finite', 'children': []}}}
        entry = measure(leafless, self.tools, repeats=1)
        self.assertEqual(entry['states'], 0)
        admit(book, leafless, entry)
        other = dict(entry, verifier='0' * 64)
        with self.assertRaises(ValueError):
            admit(book, leafless, other)

    def transcript_ops(self, directory):
        lines = (directory / 'discovery/work/transcript.jsonl').read_text().splitlines()
        import json
        return [json.loads(x)['request']['op'] for x in lines]

    def test_probe_skips_a_lone_option_and_blind_uses_no_hints(self):
        target = (10, 16)
        rows = [(target, 'N')] + [(minimal_generators(target + (m,)), outcome(minimal_generators(target + (m,))))
                                  for m in range(3, 40, 2)]
        bundle, path = golf_bundle(self.root / 'lone', target, rows)
        r = run_episode(bundle, GOLF['golf-probe'], self.root / 'lone-probe', self.tools, hints=path)
        self.assertEqual(r['status'], 'valid')
        self.assertNotIn('exact', self.transcript_ops(self.root / 'lone-probe'))
        r = run_episode(self.bundle, GOLF['golf-blind'], self.root / 'blind', self.tools, hints=self.hints)
        self.assertEqual((r['status'], r['outcome']), ('valid', 'N'))
        ops = self.transcript_ops(self.root / 'blind')
        self.assertNotIn('hint', ops); self.assertIn('exact', ops)

    def test_probe_never_submits_a_refuted_witness(self):
        # Mislabel one N child of the target as P: the probe refutes it and
        # must certify the root leaf instead.
        wrong = next(p for p, o in self.rows[1:] if o == 'N')
        rows = [(p, 'P' if p == wrong else o) for p, o in self.rows if o == 'N'] + [(self.target, 'N')]
        rows = list(dict(rows).items())
        bundle, path = golf_bundle(self.root / 'refuted', self.target, rows)
        r = run_episode(bundle, GOLF['golf-probe'], self.root / 'refuted-probe', self.tools, hints=path)
        self.assertEqual((r['status'], r['outcome']), ('valid', 'N'))
        proof = read(self.root / 'refuted-probe/certificate.json')
        self.assertEqual(proof['nodes'][key(self.target)]['rule'], 'finite')

    def test_parallel_tournament_keeps_order_and_stops_on_failure(self):
        from sylver.arena.tournament import run_tournament
        chosen = {'a': {'policy': GOLF['golf-root']}, 'b': {'policy': GOLF['golf-witness']}}
        out = self.root / 'parallel'
        entries = run_tournament([self.bundle], chosen, out, self.tools, 2, 0,
                                 hints={sha(self.bundle['manifest']): self.hints}, workers=2)
        self.assertEqual([n for n, _ in entries], ['a', 'b', 'b', 'a'])  # rotated per repeat
        runs = read(out / 'runs.json')
        self.assertEqual([r['competitor'] for r in runs], ['a', 'b', 'b', 'a'])
        # A task whose pinned hint file is missing fails at once; the queue stops.
        bad, _ = golf_bundle(self.root / 'bad', self.target, self.rows[:5])  # its hint file is not supplied
        with self.assertRaises(ValueError):
            run_tournament([bad, self.bundle], chosen, self.root / 'stopped', self.tools, 3, 0,
                           hints={sha(self.bundle['manifest']): self.hints}, workers=2)
        started = [d for d in (self.root / 'stopped').iterdir() if d.is_dir()]
        self.assertLess(len(started), 6)
        self.assertEqual(record([a, c]), 'a')


class BookOfWTests(unittest.TestCase):
    def test_w_table_accounts_for_every_obligation(self):
        from sylver.arena.common import position, profile
        from sylver.arena.golf import W, W_FINITE, W_INFINITE, W_OPEN, W_WITNESSED, w_targets
        moves = profile(W)['moves']
        groups = [set(W_WITNESSED), set(W_FINITE), set(W_INFINITE), set(W_OPEN)]
        self.assertEqual(sorted(set().union(*groups)), moves)
        self.assertEqual(sum(map(len, groups)), len(moves))
        self.assertEqual(len(w_targets()), 35)
        for m, reply in W_WITNESSED.items():
            child = position((*position((*W, m)), reply))
            self.assertEqual(profile(child)['gcd'], 1, m)   # a finite destination
        for m in W_FINITE:
            self.assertEqual(profile(position((*W, m)))['gcd'], 1, m)

    def test_short_prover_certificates_pass_the_referee(self):
        from sylver.arena.golf import ShortProver
        from sylver.arena.proof import verify
        with tempfile.TemporaryDirectory() as d:
            rows = [((4, 6), 'P'), ((4, 26), 'N')]
            digest = save(d, encode(rows))
            prover = ShortProver(Hints(path_for(d, digest), digest), build_tools(Path(d) / 'tools'), seconds=10., depth=2)
            def batch(ps):
                return [dict(position=list(p), outcome=outcome(p)) for p in ps]
            p46 = prover.prove_p((4, 6))
            self.assertEqual(p46['4,6']['rule'], 'cover')
            self.assertTrue(verify({'schema': 1, 'root': '4,6', 'nodes': p46}, snapshot(), (4, 6), batch)['valid'])
            n = prover.prove_n((4, 26), 2)
            result = verify({'schema': 1, 'root': '4,26', 'nodes': n}, snapshot(), (4, 26), batch)
            self.assertEqual((result['valid'], result['outcome']), (True, 'N'))
