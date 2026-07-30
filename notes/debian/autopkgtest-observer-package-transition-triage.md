# Triage autopkgtest failures when the tested package is only the observer

## In simple words

An autopkgtest failure is reported against the package whose test ran. That package is not automatically the component that broke. Integration-heavy tests often expose changes in package dependencies, archive composition, package-manager policy, kernels, namespaces, filesystems, or testbed configuration.

The first job is therefore to identify the first failing operation and its inputs. Patch the named package only after the failure is reduced to behavior it owns.

## Stable lesson

Treat these as separate identities:

- **observer package** — the package whose autopkgtest reports failure;
- **trigger package** — the upload or migration that caused the test to run;
- **selected package universe** — the versions chosen by APT in the testbed and generated roots;
- **owning component** — the code or policy responsible for the first failed invariant.

They may all be different.

## Failure layers

Classify the transcript before reading the final wrapper exit code.

1. **Testbed or suite selection**
   - archive labels, codenames, priorities, trust, architecture, and test restrictions;
   - unsupported distributions should be explicitly skipped or supported, not confused with a product regression.
2. **Harness preflight**
   - source formatting, lint, helper availability, generated-test syntax, and package metadata checks;
   - these failures occur before the first named behavioral case.
3. **Mirror or cache construction**
   - APT sources, pinning, Release files, host-configuration copying, and archive movement;
   - failure here says little about later package behavior.
4. **Named behavioral case**
   - retain the exact test name plus distribution, mode, variant, format, command, and first failed assertion.
5. **Cleanup and wrapper classification**
   - distinguish a real case failure from timeout, neutral result, leaked process, artifact upload, or result-classification defects.

## A repeatable reduction order

1. Preserve the complete log and package/testbed versions.
2. Record the trigger package when available.
3. Identify whether a named test started.
4. Freeze the mirror or package universe from the failing run.
5. Run the first named case alone against that frozen input.
6. Change one input at a time: trigger package, APT policy, privilege mode, namespace/mount behavior, package version, output format, or assertion.
7. Rerun after failure and verify cleanup, retained mounts, processes, locks, and temporary paths.
8. Assign ownership only when one changed input makes the invariant appear or disappear.

## Do not combine distribution results casually

A Debian source package may be copied into Ubuntu while retaining Debian-specific package tests. A failure in an Ubuntu testbed can be a portability or test-classification problem even when a Debian failure exists at the same time.

Compare suite selection, mirror assumptions, package versions, testbed backend, kernel, distribution patches, and whether the same named case was reached. Shared package version and final exit status are insufficient to claim a shared root cause.

## The mmdebstrap example

The `mmdebstrap` package test observes a broad base-system surface. Debian run `72574145` demonstrated the distinction directly:

- observer package: `mmdebstrap 1.5.7-3`;
- trigger: `migration-reference%2F0`;
- selected package universe: Debian testing with `bsdutils 1:2.42.2-1`;
- owning component: `tests/dev-ptmx`, which used `/usr/bin/script` inside a generated root without declaring `bsdutils`.

The util-linux packaging transition exposed the fixture assumption, while mmdebstrap runtime behavior was not the owner.

## Useful transcript signal

`coverage.py` prints a structured header before every case:

```text
(17/329) unshare-as-root-user-inside-chroot
dist: testing
mode: unshare
variant: apt
format: auto
```

A later `result: FAILURE` belongs to the current header. `tools/mmdebstrap_autopkgtest_log.py` extracts that first named failure while keeping mirror and preflight failures distinct.

## Version and environment limits

This note is grounded in the imported Debian `mmdebstrap 1.5.7-3` test suite and Linux Fieldwork observations from July 2026. The observer/trigger/universe/owner distinction is stable; exact test names, counts, versions, and transitions are version-specific.

## Related records

- completed historical coordination: #53;
- exact historical result and fixture fix: #84;
- durable evidence: `investigations/mmdebstrap-dev-ptmx-bsdutils/`;
- current-sid tooling and compatibility work: PR #72;
- non-Debian classification: #55;
- capability-case hook scheduling: #153.
