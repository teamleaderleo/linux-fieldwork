# `mmdebstrap` autopkgtest failure 1141078

## In simple words

Debian reports an important failure in the `mmdebstrap` package test. That test builds many Debian roots and has historically detected regressions in package transitions, runner inputs, namespace behavior, archive metadata, and `mmdebstrap` itself. This investigation preserves the report, maps the test harness, prepares a current Debian sid reproduction, and follows the first failing operation to the component that owns it.

The work activates LF-02, chrootless `DPKG_ROOT` containment, and LF-14, archive extraction and metadata contracts. LF-03 and LF-23 become relevant when evidence crosses into ID mapping or interruption cleanup.

## Question

Which first failing operation causes Debian bug `#1141078`, and which component owns that behavior?

## Source

- Project: Debian `mmdebstrap`
- Requested revision: `debian/1.5.7-3`
- Resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Candidate source commit: none
- Local source path: `upstream/mmdebstrap/`
- Import metadata: `upstream/mmdebstrap/.linux-fieldwork-source.json`
- Debian report: `https://bugs.debian.org/1141078`

## Environment

Two execution levels are prepared:

1. an offline preflight that validates the local tools, tests, source identity, shell syntax, and public-artifact redaction;
2. a privileged disposable `debian:sid-slim` container running the imported package autopkgtest through the null backend.

The full runner records the kernel, numeric identity, namespaces, subordinate-ID availability, cgroups, selected mounts, process security fields, tool versions, APT policy, installed package versions, source hashes, command, exit status, and log digest.

## Baseline behavior

The package defines one root-requiring, skippable autopkgtest. It prepares a local Debian mirror, creates an ordinary test user with subordinate UID/GID ranges, and runs `coverage.sh --exitfirst`. The shared mirror is part of test validity because rebuilding it between cases can cross a Debian archive update and invalidate root comparisons.

The package test history names breakages involving `glibc`, `debootstrap`, `fakeroot`, `tzdata`, `usrmerge`, `dpkg`, `findutils`, `base-files`, `util-linux`, `iputils-ping`, and `dash`. The report package can therefore be the observer while another component owns the failure.

## Hypotheses

1. A package transition changed expected root contents or package-script behavior.
2. The runner supplied suite, APT source, or pinning inputs that selected an inconsistent package universe.
3. A package behaves differently under `DPKG_ROOT`, chrootless execution, user namespaces, or reduced mounts.
4. Archive ordering, ownership, links, timestamps, or special metadata differ from the test expectation.
5. The runner lacks a kernel capability or mount feature assumed by the test.
6. `mmdebstrap` or its Debian patch set owns the regression.

A code change starts only after a minimal failing command distinguishes these explanations.

## Reproduction

Run the offline checks:

```sh
scripts/preflight-mmdebstrap-investigation.sh
```

Capture the canonical Debian BTS mbox:

```sh
python3 tools/debian_bug_report.py 1141078 \
  --output-dir investigations/mmdebstrap-autopkgtest-1141078/runs/bts-1141078
```

Run the current-sid package baseline inside a disposable root environment:

```sh
scripts/reproduce-mmdebstrap-autopkgtest.sh
```

After the report identifies a named case, prepare the local mirror and reduce it:

```sh
cd upstream/mmdebstrap
CMD=mmdebstrap DEFAULT_DIST=<suite> ./make_mirror.sh
CMD=mmdebstrap ./coverage.py --dist <suite> <test-name>
```

Compare retained root archives before extraction:

```sh
python3 tools/tar_manifest.py left.tar -o left.manifest.jsonl
python3 tools/tar_manifest.py right.tar -o right.manifest.jsonl
python3 tools/manifest_diff.py left.manifest.jsonl right.manifest.jsonl --json > diff.json
```

## Results

Established so far:

- the source revision and package test entrypoint are mapped;
- the test's shared-mirror, suite-selection, ordinary-user, subordinate-ID, and timeout behavior are mapped;
- prior package-trigger history is recorded;
- root archive manifest and field-level comparison tools are implemented;
- traversal paths, exact link targets, archive ordering, timestamp drift, content drift, and absent-versus-null fields have regression coverage;
- Linux context capture excludes host and account names by default;
- Debian BTS mbox capture is implemented with size limits, message metadata, referenced URLs, and SHA-256 provenance;
- an offline preflight and a current-sid full-run script are present.

A complete Debian package run has yet to execute in the available session. Local outbound DNS is unavailable, and GitHub events created through the connected repository tool did not start Actions. Those limits are recorded in `results/local-validation.md`.

## Interpretation

The strongest current lead is a package-transition or runner-input failure. The reported source tag remained `1.5.7-3` while Debian's package archive continued changing. A comparable report, Debian bug `#1085450`, began as an `mmdebstrap` failure and moved to `sbuild` after suite selection conflicted with copied host APT configuration.

This evidence supports careful reproduction and rejects speculative edits. It does not identify the owning component yet.

## Evidence boundary

Local validation covers Python behavior, shell syntax, redaction, and source mapping. It does not cover Debian package installation, the original debci backend, the original trigger package universe, other architectures, or a complete `coverage.sh` run.

A current-sid pass would show that today's archive lacks the historical failure. A decisive historical reproduction requires the original trigger versions and a matching snapshot or retained mirror.

## Next step

Run the canonical mbox capture and full current-sid baseline from an environment with outbound Debian access. Read the first failing test and trigger package from the retained logs, then change one input per reduced run against a frozen mirror.

## Authority

Upstream contact is unauthorized. No Debian issue, email, merge request, patch submission, comment, or review has been created by this investigation.
