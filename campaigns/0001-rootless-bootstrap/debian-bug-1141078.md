# Debian bug 1141078: mmdebstrap autopkgtest fails

## In simple words

Debian records an important `mmdebstrap` autopkgtest failure against version `1.5.7-3`. The package test exercises a broad Debian bootstrap system, so the package named by the report may be the observer rather than the owner. This dossier follows the first failing operation through the runner, APT policy, local mirror, package scripts, namespace behavior, and `mmdebstrap` code.

## Public record

- Bug: `https://bugs.debian.org/1141078`
- Package: `mmdebstrap`
- Title: `mmdebstrap autopkgtest fails`
- Severity: important
- Found in: `mmdebstrap/1.5.7-3`
- Reporter: Benjamin Drung
- Reported: 2026-06-29 12:59:01 UTC
- Imported Debian revision: `debian/1.5.7-3`
- Imported commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Upstream contact authorization: **false**

## Retrieval boundary

Search indexing exposes the report metadata, while the detailed BTS transcript remains unavailable through the interactive retrieval path used for reconnaissance. The workflow now fetches the canonical mbox directly, stores its SHA-256 digest, summarizes every message header and referenced URL, and uploads the capture as a temporary repository artifact.

```bash
python3 tools/debian_bug_report.py 1141078 \
  --output-dir campaigns/0001-rootless-bootstrap/runs/bts-1141078
```

The mbox is evidence, not source code. Review its contents before retaining any portion in Git.

## Test harness map

The Debian package defines one `testsuite` autopkgtest with these important properties:

- it requires root and may return the skippable status;
- it installs a large set of bootstrap, archive, comparison, namespace, and filesystem tools;
- it derives `stable`, `testing`, or `unstable` from the highest-priority APT source supplying `base-files`;
- it creates or selects an ordinary test user and ensures subordinate UID/GID ranges exist;
- it builds a local Debian mirror cache under a 50-minute limit;
- it runs the full `coverage.sh --exitfirst` suite with the installed `mmdebstrap` package;
- it disables QEMU and binfmt paths in this autopkgtest environment;
- it can spend roughly two hours in the shared-cache test phase.

The shared cache is part of the test's validity. Rebuilding it between cases can cross a Debian archive update and create roots from different package universes.

`coverage.py` reads `shared/cache/debian/dists/<suite>/InRelease` before parsing the requested test names. Even a one-test reduction needs a prepared mirror or a retained cache from the full run.

## Historical signal

`debian/tests/control` documents earlier packages that broke this suite, including `glibc`, `debootstrap`, `fakeroot`, `tzdata`, `usrmerge`, `dpkg`, `findutils`, `base-files`, `util-linux`, `iputils-ping`, and `dash`. Several failures affected named tests such as `chrootless`, `check-against-debootstrap-dist`, `multiple-include`, and `missing-dev-sys-proc-inside-the-chroot`.

A comparable 2024 report, Debian bug `#1085450`, began as an `mmdebstrap` failure and was reassigned to `sbuild`. The runner supplied a non-empty suite while using the host-APT-copy hook, which selected package versions from conflicting inputs. This precedent makes the failing command, APT policy, suite selection, and package universe primary evidence.

## First questions

1. Which autopkgtest command and testbed backend failed?
2. Which Debian suite, architecture, kernel, and package set were active?
3. Which package upload triggered the test?
4. Did the failure occur while creating the local mirror, constructing a root, running hooks, comparing output, or cleaning up?
5. Does the same failure occur in a fresh Debian sid null testbed?
6. Does it occur against the package universe captured by the original report?
7. Is the first divergent component `mmdebstrap`, another package under transition, the test harness, or the runner environment?

## Reproduction levels

### Level 1: Debian sid baseline

The repository workflow runs the imported source tests against current Debian sid in a privileged disposable container:

```bash
scripts/reproduce-mmdebstrap-autopkgtest.sh
```

This answers whether the current archive still exhibits a failure. A passing result means the original transition may have moved; it does not erase the original failure.

### Level 2: Report-matched environment

After reading the BTS mbox and referenced CI log, reproduce:

- suite and architecture;
- testbed backend;
- trigger package and version;
- APT sources and pinning;
- kernel and namespace capability;
- exact `mmdebstrap` binary version;
- first failing test name.

### Level 3: Frozen single-test reduction

Prepare the local mirror first, then run the named case:

```bash
cd upstream/mmdebstrap
CMD=mmdebstrap DEFAULT_DIST=<suite> ./make_mirror.sh
CMD=mmdebstrap ./coverage.py --dist <suite> <test-name>
```

Record Release-file hashes, package index hashes, selected versions, and retrieval time. A decisive historical reproduction needs a snapshot or retained mirror matching the report.

### Level 4: Ownership experiment

Change one axis per run:

- trigger package version;
- suite or APT policy;
- root versus unshare mode;
- one hook;
- one package;
- one output format;
- one assertion.

When roots exist on both sides, compare complete manifests before suppressing timestamp or archive-order fields:

```bash
python3 tools/tar_manifest.py left.tar -o left.manifest.jsonl
python3 tools/tar_manifest.py right.tar -o right.manifest.jsonl
python3 tools/manifest_diff.py left.manifest.jsonl right.manifest.jsonl --json > diff.json
```

## Competing hypotheses

- A package transition changed expected root contents while the test cache or trigger relationship exposed the change.
- The runner supplied APT sources, pinning, or a suite value that selected inconsistent package sets.
- Mirror movement produced roots from different package universes during one attempted reproduction.
- A package changed behavior under `DPKG_ROOT`, chrootless installation, user namespaces, or missing `/dev`, `/sys`, or `/proc` mounts.
- Rootless UID/GID mapping changed metadata or hook behavior.
- The runner lacks a capability, kernel feature, or mount option assumed by the suite.
- The test expectation encodes an obsolete package set or filename.
- `mmdebstrap` or its Debian patch set contains the regression.

## Evidence required for a code change

A candidate patch needs:

- a minimal failing command;
- a retained baseline failure;
- a passing candidate run;
- a regression test aimed at the owning behavior;
- exact source and package revisions;
- an explanation of why the change belongs in `mmdebstrap` instead of another component;
- remaining uncertainty and compatibility risk.

## Current result

- Test harness and dependency history mapped.
- BTS mbox capture implemented.
- Current-sid full reproduction workflow implemented.
- Draft pull request opened inside Linux Fieldwork to execute and retain the checks.
- Cause remains unknown pending the captured transcript and first completed run.
- No Debian or upstream interaction performed.
