# Upstream merge-request draft

No publication is authorized.

## Title

Run package tests phase-correctly on current sid

## Summary

This series lets the Debian package test progress through current-sid compatibility setup and execute the no-`CAP_SYS_ADMIN` case with the archive baseline produced under the same command and hook configuration.

It:

- processes Deb822 source paragraphs through exploded entries after rooting their raw output file paths;
- invokes the installed mmdebstrap binary through `/usr/bin/mmdebstrap`, independent of later directory changes;
- sends customize-hook SIGINT to the complete process group through a dash builtin spelling accepted on current sid;
- runs `root-without-cap-sys-admin` without mount-dependent host APT hooks while preserving ordinary failure statuses;
- executes `create-directory` immediately before that consumer;
- lets broad coverage run `create-directory` again so later consumers receive a baseline generated with broad host hooks.

## Failure sequence

The previous package path stopped successively on:

1. a `Deb822SourceEntry` assertion;
2. loss of a relative command after a directory change;
3. procps rejection of the process-group signal arguments;
4. a bind-mount attempt after the capability case dropped `CAP_SYS_ADMIN`;
5. a missing `tar1.txt` prerequisite;
6. reuse of a hook-free `tar1.txt` by broad host-hook consumers.

The phase-scoped candidate cleared the focused producer and capability consumer, regenerated the broad baseline, completed 154 package tests, and reached the independent `chrootless` directory-mtime result.

## Commit organization

1. `tests: accept Deb822 entries in sourcesfilter`
2. `tests: use the absolute installed mmdebstrap path`
3. `tests: use current-sid process-group SIGINT syntax`
4. `tests: run the capability case with a phase-local hook-free baseline`

## Status semantics

The focused phase keeps child statuses such as 1 and 2 authoritative. GNU `timeout` status 124 maps to autopkgtest status 77. Empty consumer selection fails before child execution.

## Scope

The series changes package-test source only. It excludes reproduction workflows, artifact collection, temporary command proxies, generic signal probes, and Linux Fieldwork guard harnesses. The later `chrootless` timestamp policy remains separate.

## Test plan before submission

- apply all four patches with zero fuzz and zero offset to current Salsa `master`;
- compile `coverage.py` and `debian/tests/sourcesfilter`;
- check shell syntax for `debian/tests/testsuite` and `tests/sigint-during-customize-hook`;
- run focused Deb822 and process-group signal tests on current sid;
- run the focused hook-free producer/consumer and broad producer/consumer paths;
- run the Debian package tests until the next independent result;
- repeat after cleanup and record exact package versions and artifact hashes.

## Compatibility boundary

The signal spelling is selected for current Debian sid with dash on Linux. The installed command path follows the Debian package layout. The new metadata class remains bounded to the capability consumer, with one explicit archive producer prerequisite.
