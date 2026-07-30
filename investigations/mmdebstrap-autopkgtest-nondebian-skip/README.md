# mmdebstrap autopkgtest neutral skip on unsupported archive identities

## In simple words

The Debian `mmdebstrap` package test is marked `skippable`, but it currently exits as a hard failure when the host APT archive does not identify itself as Debian `stable`, `testing`, or `unstable`.

The candidate changes that one unsupported-environment exit from `1` to `77`. Debian suite selection remains unchanged. The test then reports a neutral result before mirror construction or behavioral cases begin.

## Coordination and duplicate search

- Canonical Linux Fieldwork issue: #55
- Debian bug triage coordination: #53
- Durable transition-triage branch: PR #60
- Primary Debian bug investigation: PR #9

Open and closed issues and pull requests, the imported source, adjacent test metadata, and repository notes were searched. No existing candidate covered this exact classification boundary.

## Exact source boundary

- Imported package: Debian `mmdebstrap 1.5.7-3`
- Source file: `upstream/mmdebstrap/debian/tests/testsuite`
- Test metadata: `upstream/mmdebstrap/debian/tests/control`
- Candidate patch: `0001-skip-unsupported-apt-archives.patch`

The package test declares `Restrictions: allow-stderr, needs-root, skippable`.

## Source and call map

The shell entrypoint runs with:

```sh
set -exu
```

It assigns `DEFAULT_DIST` from an embedded Python selector. The selector:

1. initializes `apt_pkg`;
2. examines candidate files for `base-files`;
3. ignores missing and untrusted source-list indexes;
4. accepts only archive names `stable`, `testing`, or `unstable`;
5. chooses the accepted file with the highest APT priority;
6. dumps APT file metadata and exits when no accepted archive exists.

The assignment is the first distribution-specific control point. Mirror creation and `coverage.sh` occur later.

## Baseline

For a trusted synthetic APT file with:

```text
archive=resolute
origin=Ubuntu
priority=500
```

the unmodified embedded selector prints the unsupported-archive diagnostic and exits `1`.

Under `set -e`, the assignment stops the package test with the same hard-failure status. No mirror or mmdebstrap behavioral case is reached.

## Candidate

Change only:

```diff
-	exit(1)
+	exit(77)
```

The diagnostic and APT metadata dump remain intact. No Ubuntu suite mapping, mirror substitution, or claim of Ubuntu support is introduced.

## Executable regression

`tests/test_mmdebstrap_autopkgtest_suite_selection.py`:

- applies the retained patch to an exact temporary source copy with `patch -p1`;
- extracts the real embedded Python selector from the shell script;
- supplies a fake `apt_pkg` module with controlled package files, trust, and priorities;
- requires trusted Debian archive priority selection to remain unchanged;
- requires an untrusted higher-priority candidate to remain ignored;
- proves the unmodified selector returns `1` for a non-Debian archive;
- requires the candidate selector to return `77` for the same input;
- executes the candidate selector inside `/bin/sh` command substitution with `set -eu` and requires shell exit `77` with no later command executed.

The baseline `1` result is the negative control demonstrating that the regression would fail against the imported source.

## Interpretation

This is a package-test classification defect, not evidence that `mmdebstrap` itself cannot create Ubuntu roots. The current package test is deeply Debian-specific after suite selection as well, including its local Debian mirror, distribution matrix, and package expectations.

The bounded fix states that unsupported archive identities are outside this test's current contract. Real Ubuntu support would need a separate design and broader tests.

## Evidence limits

The synthetic selector tests do not boot an Ubuntu autopkgtest VM or run the full two-hour package suite. They exercise the exact selector code and shell exit boundary under controlled APT metadata.

The candidate does not identify the owner of Debian CI run `72574145` and must not be used to close Debian bug `#1141078`.

## Cleanup and rerun

Tests use a temporary directory, copy one source file, create one fake Python module, apply the patch, and remove the directory through `unittest` cleanup. They perform no package installation, mount, namespace, root operation, or network access.

Repeated selector runs are independent because all APT inputs are passed through a fresh subprocess environment.

## Self-review

- exact source and test restriction were read;
- candidate changes one exit classification only;
- Debian selection behavior is asserted;
- trust and priority behavior is asserted;
- baseline hard failure is retained as a negative control;
- `/bin/sh` and `set -e` propagation are asserted;
- unsupported-environment diagnostics remain visible;
- no later test behavior is masked in supported Debian environments;
- no imported source file is directly modified; the candidate is retained as an applyable patch;
- no upstream contact is included.

## Reusable note

See `notes/debian/skippable-autopkgtests-must-classify-unsupported-testbeds.md`.

## Disposition

**Fix candidate.** Retain for exact-head CI and peer review. If accepted locally, decide separately whether to apply it to the imported tree or prepare an authorized upstream packet.

## Authority

No Debian, Ubuntu, or other external issue, email, merge request, patch submission, comment, or review is authorized by this investigation.
