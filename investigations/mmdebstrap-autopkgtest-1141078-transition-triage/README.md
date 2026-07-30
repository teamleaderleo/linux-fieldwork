# Debian mmdebstrap autopkgtest 1141078 transition triage

## In simple words

Debian CI reports that `mmdebstrap 1.5.7-3` fails its package test. A Linux Fieldwork run first encountered a formatting defect introduced by the local TMPDIR candidate, so that run did not reach the unknown Debian failure. The formatting defect is repaired on `main`.

This record separates local harness failures, Ubuntu portability, Debian archive transitions, and the first real named behavioral test. The current answer is that Debian ownership remains unknown; archive/package-universe mismatch and namespace or mount behavior remain the leading classes until a retained transcript names the first case.

## Coordination and existing-work search

- Central Linux Fieldwork issue: #53
- Primary draft investigation: PR #9
- Local formatting repair: PR #26
- Historical Debian log retrieval attempt: PR #31
- Repository workflow defect: #54
- Non-Debian suite-selection classification defect: #55

Open and closed issues, pull requests, `targets/`, `notes/`, `investigations/`, and the imported source were searched before this record was created. No existing issue coordinated Debian bug `#1141078`; issue #53 now owns that role.

## Exact source boundary

- Project: Debian `mmdebstrap`
- Package revision: `1.5.7-3`
- Imported source commit recorded by the target map: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Local source: `upstream/mmdebstrap/`
- Package-test metadata: `upstream/mmdebstrap/debian/tests/control`
- Package-test entrypoint: `upstream/mmdebstrap/debian/tests/testsuite`
- Suite driver: `upstream/mmdebstrap/coverage.sh`
- Case scheduler: `upstream/mmdebstrap/coverage.py`
- Case registry: `upstream/mmdebstrap/coverage.txt`

This research branch started from repository `main` after PR #26 repaired the local perltidy mismatch. It does not edit the imported mmdebstrap source.

## Public record

- Debian bug: `#1141078`
- Reported package: `mmdebstrap 1.5.7-3`
- Referenced Debian CI run: `72574145`
- Canonical archived-log convention gives:
  `https://ci.debian.net/data/autopkgtest/testing/amd64/m/mmdebstrap/72574145/log.gz`

The original transcript and trigger package are not retained in this branch.

## Source and test map

### Suite selection

`debian/tests/testsuite` inspects candidate files for `base-files`, ignores untrusted entries, and accepts only APT archive identities `stable`, `testing`, or `unstable`. It chooses the accepted file with the highest APT priority.

When no accepted archive exists, the embedded Python exits `1`. Because the shell runs with `set -e`, that becomes a hard autopkgtest failure even though the test is marked `skippable`. Issue #55 tracks the explicit policy decision and regression required for non-Debian testbeds.

### Shared mirror

The entrypoint builds a local cache before behavioral tests. The first mirror phase uses:

```text
USE_HOST_APT_CONFIG=yes
```

This protects transition testing but also makes host APT sources, pinning, and selected package versions part of the test input. Mirror failure is converted to exit `77`, not a behavioral package failure.

### Pre-suite gates

Before running a named case, `coverage.sh` checks the installed `mmdebstrap` with `perltidy`, maximum line length, `perlcritic`, and `pod2man`. It also checks Python and shell helpers.

The Linux Fieldwork run `30514378292` stopped here because the local TMPDIR candidate used a two-line assignment that current Debian `perltidy` collapsed. PR #26 repaired that local formatting. This observation must not be attributed to Debian run `72574145`.

### Named behavioral cases

`coverage.py` expands `coverage.txt` into distribution, mode, variant, and format combinations. Before each case it prints:

```text
(<index>/<total>) <test-name>
dist: <suite>
mode: <mode>
variant: <variant>
format: <format>
```

A later `result: FAILURE` identifies the current case. `tools/mmdebstrap_autopkgtest_log.py` classifies that signal and keeps mirror, preflight, wrapper-only, and passing outcomes distinct.

### Transition-sensitive surfaces

The suite includes early and later cases that exercise:

- `unshare --mount --propagation unchanged` inside a chroot;
- recursive bind mounts and lazy unmounts;
- `pivot_root`;
- nested unprivileged user namespaces;
- subordinate UID/GID setup;
- root, unshare, fakechroot, and chrootless modes;
- copied host APT configuration and generated local mirrors;
- package-root and archive comparisons;
- maintainer scripts, hooks, device nodes, and cleanup.

## Established observations

1. **The first Linux Fieldwork failure was local.** It occurred before a named test and is repaired on `main`.
2. **Ubuntu is a separate classification problem.** A non-Debian archive can fail during suite detection before mmdebstrap behavior is tested. Issue #55 tracks this.
3. **The observer package may not own the failure.** The test metadata explicitly records historical regressions caused by numerous other base-system packages.
4. **APT/package-universe mismatch is a strong class.** The test copies host APT configuration into mirror construction, and Debian bug `#1085450` provides a close ownership precedent involving incompatible suite and host-APT inputs.
5. **Namespace and mount behavior is the strongest concrete subsystem lead.** `util-linux`, libmount, kernel namespace, and mount-propagation changes overlap directly with named tests. No named failing case yet proves this owner.
6. **Current repository CI has an infrastructure gap.** The main workflow references PR #9 tooling absent from `main`; issue #54 tracks the ownership model and repair.

## Hypothesis ranking

1. host APT policy or selected package-universe inconsistency;
2. `util-linux` / libmount / `unshare` / mount-propagation behavior;
3. glibc or fakechroot interaction;
4. systemd, kernel, or testbed namespace behavior;
5. another base-system package changing expected root contents or package scripts;
6. mmdebstrap-owned source regression.

The ranking is provisional and must move when a named failing command exists.

## Executable probe

Classify a retained transcript:

```sh
python3 tools/mmdebstrap_autopkgtest_log.py path/to/log
python3 tools/mmdebstrap_autopkgtest_log.py path/to/log --json
```

The parser reports one of:

- `mirror` — local cache construction failed;
- `coverage-preflight` — formatter, lint, or helper gate failed before named cases;
- `coverage-case` — a named case emitted `result: FAILURE`;
- `pass` — autopkgtest reported success;
- `unknown` — only wrapper-level failure evidence exists.

Synthetic tests include a passing negative control, first-failure retention, ANSI/timestamp prefixes, mirror failure, preflight failure, named case failure, and wrapper-only ambiguity.

## Next distinguishing run

After issue #54 or PR #9 supplies coherent reusable tooling:

1. run the exact imported package test from current `main` with the formatting repair;
2. retain the complete console, package versions, APT policy, Release hashes, and mirror state;
3. classify the transcript with the parser in this branch;
4. preserve the first named generated `shared/test.sh` and its command;
5. rerun only that named case against the same mirror;
6. vary one transition-sensitive input at a time;
7. check cleanup and immediate rerun behavior.

## Evidence limits

This record does not contain the original Debian CI log, trigger package, frozen June 2026 mirror, or a post-formatting full current-sid run. Static source reading establishes control flow and distinguishing signals, not historical ownership.

The transition list is a triage aid. It is not evidence that any listed package caused run `72574145`.

## Cleanup and rerun

The work added no privileged probe, mount, package installation, temporary root, external service, or retained raw log. The parser is read-only and accepts a path or standard input. Its tests use in-memory synthetic text and leave no state.

## Self-review

- exact source and adjacent test drivers were read;
- the parser asserts the written phase contract rather than merely printing lines;
- the passing transcript is a negative control for false failure classification;
- first-failure behavior is asserted when later failures exist;
- ANSI and timestamp prefixes are covered;
- wrapper-only ambiguity remains explicit;
- no imported source, privilege boundary, destructive path, or external tracker was changed;
- claims stop before historical ownership.

## Reusable note

See `notes/debian/autopkgtest-observer-package-transition-triage.md`.

## Disposition

**Expand.** Retain the classifier and dossier, repair the repository execution gate, then obtain the first named failure before proposing a product change for Debian bug `#1141078`.

## Authority

No Debian, Ubuntu, or other upstream issue, email, merge request, patch submission, comment, or review is authorized by this investigation.
