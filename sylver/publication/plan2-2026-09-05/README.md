# Sylver Coinage verification bundle — 2026-09-05

Start with [the research note](REPORT.md) and
[the certificate's response table](CERTIFICATE.md).

This release independently confirms the published P-position
{16,26,54,60,62} and corrects our project's U/X/Q reduction.
Opening 16 remains unresolved. The mathematical dependencies are
explicit in the certificate; no private documents or campaign caches
are required.

## Verify the release

Requirements: Linux or another POSIX system, Python 3.10 or newer,
and `g++` with C++20 support. The core verification has no Python package
dependencies and makes no network requests. Native processes are capped
at 4 GiB of address space; the default timeout is 300 seconds per position.
Computation times depend on the machine. A timeout is a failed verification,
never evidence for an outcome.

Run from this directory:

```sh
sha256sum -c SHA256SUMS
python -m unittest discover -s tests -q
python verify.py --output /tmp/sylver-plan2-verification.json
```

The default verifier rebuilds the native executable in a temporary directory
and recomputes **every finite leaf**, alongside all graph and arithmetic
checks. It prints the published P-position dependencies separately.
`evidence/verification.json` contains the release preparation's successful
replay, for comparison. The fresh computation is the substantive check;
the SHA-256 file detects changed bytes but is not an authenticity signature.

A quick structural audit, which **does not recompute finite outcomes**, is:

```sh
python verify.py --structure-only
```

## Rebuild the evidence from public inputs

```sh
python build_certificate.py --output rebuilt-evidence
python verify.py --certificate rebuilt-evidence/certificate.json
```

This runs longer than replaying the certificate because it rediscovers
missing replies by ascending odd scans. No seed cache or imported claim
file is read. The response tables in the included project source provide
other candidate replies; each finite destination is recomputed. Named
published infinite P results remain explicit mathematical dependencies.
The builder checkpoints completed facts so a run can resume in the same
directory. To obtain a completely fresh run, use a new output directory.

## Contents and scope

- `REPORT.md`: result, correction, and remaining research frontier.
- `CERTIFICATE.md`: all 38 root obligations and dependency inventory.
- `evidence/`: certificate, fresh search logs, and verification receipt.
- `build_certificate.py`, `verify.py`: public reconstruction and checking.
- `sylver/`: exact solver, periodicity control, proof graph, and generic
  campaign/import tools, with their required local modules.
- `tests/`: graph, importer, campaign, and public-verifier checks. Parser
  prose examples are synthetic.
- `SOURCE_MANIFEST.json`, `SHA256SUMS`: source provenance and integrity.

The optional DOCX importer additionally needs `pandoc` and caller-supplied
documents in its expected `g=2` layout. It treats extracted replies as
unverified claims. It is not part of the public certificate reproduction.
The broader campaign's 33 certificates and private corpus audit are not
included or represented as independently reproducible from this release.

The bundle is a prepared release artifact. Publication or distribution
is a separate action.
