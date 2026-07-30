# mmdebstrap dev-ptmx dependency transition

## In simple words

Debian CI run `72574145` failed because the `dev-ptmx` test uses `script(1)` inside the generated apt-variant root but does not request the package that provides it. The test passed while `bsdutils` was Essential and failed after that packaging assumption changed.

## Canonical records

- Focused issue: #84
- Central transition investigation: #53
- Historical capture: closed PR #82
- Imported source: `upstream/mmdebstrap/tests/dev-ptmx`
- Candidate patch: `0001-include-bsdutils.patch`
- Historical signature: `historical-failure.txt`
- Regression: `tests/test_mmdebstrap_dev_ptmx_dependencies.py`

## Exact source boundary

The test constructs one apt-variant root with:

```text
--include=gcc,libc6-dev,python3,passwd
```

It then runs `script` twice through `chroot "$1"`: once as root and once through `runuser`. The outer `script -qfec` belongs to the autopkgtest testbed; only the two inner commands depend on the generated root package set.

## Historical evidence

The recovered Debian testing amd64 run reached case `(252/283) dev-ptmx --mode=root` after 158 passes and 93 skips. Its first unavailable command was:

```text
chroot: failed to run command ‘script’: No such file or directory
```

The failing archive used `bsdutils 1:2.42.2-1`. The captured root include set did not contain `bsdutils`.

## Candidate

Add `bsdutils` to the existing include set and change nothing else:

```diff
- --include=gcc,libc6-dev,python3,passwd
+ --include=bsdutils,gcc,libc6-dev,python3,passwd
```

This is a package-test dependency correction. It does not change mmdebstrap runtime behavior or util-linux packaging.

## Regression contract

The executable regression:

1. proves the unmodified imported source lacks `bsdutils` while containing two inner `script` hooks;
2. applies the retained patch to an exact temporary source copy;
3. requires the patched include set to be exactly `bsdutils,gcc,libc6-dev,python3,passwd`;
4. requires every other byte, including hook order, to remain unchanged;
5. validates the compact historical failure signature.

## Validation boundary

The local regression proves source ownership and the minimal candidate. A full current-mirror execution of the named `dev-ptmx --mode=root --variant=apt` case remains the dynamic confirmation. A current pass will validate the candidate against the present package universe but will not recreate the exact June 2026 archive.

## Cleanup and safety

The regression operates only on a `TemporaryDirectory`, applies one text patch, and creates no root filesystem, process, listener, mount, package state, or persistent temporary path.

## Disposition

Retain the focused candidate and run the named case through the reusable Debian harness when available. No Debian or external upstream contact is included or authorized.
