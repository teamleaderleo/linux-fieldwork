# Debian bug 1141078: mmdebstrap autopkgtest fails

## In simple words

Debian currently records an important `mmdebstrap` autopkgtest failure against version `1.5.7-3`. This dossier defines the contained investigation. It makes no claim about the cause until the original transcript and a local reproduction identify the first failing operation.

## Public record

- Bug: `https://bugs.debian.org/1141078`
- Package: `mmdebstrap`
- Title: `mmdebstrap autopkgtest fails`
- Severity: important
- Found in: `mmdebstrap/1.5.7-3`
- Reporter: Benjamin Drung
- Reported: 2026-06-29 12:59:01 UTC
- Upstream contact authorization: **false**

## Retrieval boundary

The package index exposed the metadata above during initial reconnaissance. The detailed bug transcript was unavailable through the retrieval path used at that time. Preserve the complete BTS transcript or mbox before drawing conclusions from the report.

Store the transcript retrieval date and a SHA-256 hash beside the retained copy. Keep email addresses and message headers intact in the private working artifact when needed for provenance; commit only material suitable for the public repository.

## First questions

1. Which autopkgtest command and testbed backend failed?
2. Which Debian suite, architecture, kernel, and package set were active?
3. Did the failure occur while creating the local mirror, constructing a root, running hooks, comparing output, booting a VM, or cleaning up?
4. Does the same failure occur with the imported source revision?
5. Does it occur against a frozen package snapshot?
6. Does privileged execution change the outcome?
7. Is the first divergent component `mmdebstrap`, another package under transition, the test harness, or the runner environment?

## Reproduction plan

### 1. Preserve the report

Capture:

- full BTS transcript or mbox;
- referenced CI job and artifacts;
- exact failing command;
- package versions and architecture;
- first error plus enough preceding log to establish state.

### 2. Capture the host

```bash
scripts/capture-linux-context.sh campaigns/0001-rootless-bootstrap/runs/<run-id>/context.md
```

### 3. Run the smallest named test

The imported test suite supports individual tests through `coverage.py`. Begin with the exact failing test when known. Use the source revision and environment from the report.

```bash
cd upstream/mmdebstrap
CMD=./mmdebstrap ./coverage.py --dist unstable <test-name>
```

Record any required local mirror setup separately. Keep network retrieval and test execution as distinct steps.

### 4. Freeze package input

A moving Debian mirror can invalidate repeated comparisons during a package transition. Record Release-file hashes, package index hashes, selected package versions, and retrieval time. Prefer a snapshot or retained local mirror for the decisive reproduction.

### 5. Minimize

Reduce the failure along these axes:

- one suite;
- one architecture;
- one mode;
- one variant;
- one hook;
- one package trigger;
- one output format;
- one failing assertion.

### 6. Compare roots

```bash
python3 tools/tar_manifest.py left.tar -o left.manifest.jsonl
python3 tools/tar_manifest.py right.tar -o right.manifest.jsonl
python3 tools/manifest_diff.py left.manifest.jsonl right.manifest.jsonl --json > diff.json
```

Repeat with `--ignore-field mtime` only after preserving the full comparison. Timestamp normalization can hide a meaningful package-script or archive-ordering defect.

## Competing hypotheses

- A package transition changed expected root contents while the test cache or trigger set remained stale.
- Mirror movement produced roots from different package universes during one long test run.
- A recent package changed behavior under `DPKG_ROOT`, chrootless installation, user namespaces, or missing `/dev`, `/sys`, or `/proc` mounts.
- Rootless UID/GID mapping changed metadata or hook behavior.
- The autopkgtest runner lacks a capability, kernel feature, binfmt handler, or mount option assumed by the suite.
- The test expectation itself encodes an obsolete package set or filename.
- `mmdebstrap` introduced a regression in version `1.5.7-3` or its Debian patch set.

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

Investigation initialized. Cause unknown. No external interaction performed.
