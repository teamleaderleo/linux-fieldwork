# Debian bug 1141078 dossier

## In simple words

Debian records an important `mmdebstrap` autopkgtest failure against version `1.5.7-3`. The package test exercises a broad bootstrap workflow, so the report title identifies where the failure was observed. This dossier tracks the runner, APT policy, mirror, package scripts, namespaces, archive semantics, and `mmdebstrap` code until the first failing operation identifies an owner.

## Public record

- Bug: `https://bugs.debian.org/1141078`
- Package: `mmdebstrap`
- Title: `mmdebstrap autopkgtest fails`
- Severity: important
- Found in: `mmdebstrap/1.5.7-3`
- Reporter: Benjamin Drung
- Reported: 2026-06-29 12:59:01 UTC
- Imported revision: `debian/1.5.7-3`
- Imported commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Upstream contact authorization: **false**

## Report capture

The repository tool preserves the canonical BTS mbox, records its size and SHA-256 digest, summarizes message headers and referenced URLs, and keeps the raw mail outside Git:

```sh
python3 tools/debian_bug_report.py 1141078 \
  --output-dir investigations/mmdebstrap-autopkgtest-1141078/runs/bts-1141078
```

Review generated mail artifacts before publication.

## Test harness map

The Debian package defines one `testsuite` autopkgtest with these properties:

- root is required and a neutral skip result is allowed;
- dependencies cover bootstrap, archive, comparison, namespace, and filesystem tools;
- `stable`, `testing`, or `unstable` is derived from the highest-priority APT source supplying `base-files`;
- an ordinary user is created or selected and subordinate UID/GID ranges are ensured;
- a local Debian mirror cache is prepared under a 50-minute limit;
- the installed `mmdebstrap` package runs the full `coverage.sh --exitfirst` suite;
- QEMU and binfmt paths are disabled in this package-test environment;
- the shared-cache phase can consume roughly two hours.

The shared cache prevents different cases from crossing a Debian archive update. `coverage.py` reads the cached suite `InRelease` before it selects a named test, so a single-test reduction still needs a prepared mirror.

## Historical signal

`debian/tests/control` records prior breakages caused by packages including `glibc`, `debootstrap`, `fakeroot`, `tzdata`, `usrmerge`, `dpkg`, `findutils`, `base-files`, `util-linux`, `iputils-ping`, and `dash`.

Debian bug `#1085450` provides a close precedent. An apparent `mmdebstrap` failure was reassigned to `sbuild` after the runner supplied a suite that conflicted with the host-APT-copy hook and selected mismatched package versions. Runner command, suite selection, APT policy, and trigger package therefore rank ahead of an immediate source patch.

## Questions for the first retained run

1. Which backend and exact command failed?
2. Which suite, architecture, kernel, and package set were active?
3. Which upload triggered the package test?
4. Did failure begin in mirror creation, root construction, hooks, output comparison, or cleanup?
5. Which named test failed first?
6. Does current Debian sid reproduce it?
7. Does a frozen package universe reproduce it?
8. Which single changed input makes the failure appear or disappear?

## Reduction order

1. Preserve the full report and referenced CI log.
2. Capture APT sources, priorities, Release hashes, package versions, architecture, and kernel.
3. Run the current-sid baseline once.
4. Retain the local mirror from a failing run.
5. Run the named case alone against that mirror.
6. Vary trigger package, suite or pinning, privilege mode, hook, package, output format, and assertion one at a time.
7. Compare root archives with every field enabled before ignoring timestamp or ordering noise.

## Patch threshold

A candidate change needs:

- a minimal failing command;
- retained baseline evidence;
- a passing candidate run under the same inputs;
- a regression test aimed at the owning behavior;
- exact source and package revisions;
- a reason the change belongs in `mmdebstrap`;
- stated compatibility risk and remaining uncertainty.

## Current result

The test harness and dependency history are mapped. Capture and reproduction tools exist. The owning component remains unknown because the original transcript and a complete package run have yet to execute in the available environment.
