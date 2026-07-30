# Chrootless maintainer-script temporary containment

## Defect

The chrootless environment scrub intentionally removes the caller's ambient environment before invoking `dpkg`. It originally removed `TMPDIR` without supplying a replacement. Maintainer scripts using `mktemp` therefore fell back to host `/tmp`, outside the selected target root.

Issue #69 retains the direct reproduction.

## Correction

`chrootless_dpkg_environment()` now receives the selected target root and supplies:

```text
TMPDIR=<target>/tmp
```

Before constructing the clean environment it:

1. rejects a symlink at `<target>/tmp`;
2. creates the directory when absent;
3. rejects an existing non-directory;
4. enforces mode `01777`.

Both chrootless dpkg paths pass the selected root:

- direct `run_essential()` execution;
- apt-managed `run_install()` execution through `DPkg::Options`.

The caller's arbitrary `TMPDIR` is never copied into the package-script environment.

## Regression contract

`tests/test_mmdebstrap_chrootless_tmpdir.py` executes the exact helper extracted from the imported source and requires:

- target-contained `TMPDIR` assignment;
- mode `01777`;
- a real `mktemp` directory below the target;
- cleanup of that directory;
- refusal of symlink and non-directory targets;
- both production call sites to pass the target root.

The mutation control removes only the `TMPDIR` assignment and must reproduce a created path below host `/tmp`.

The full chrootless security fixture also records package-script `TMPDIR` and created paths for apt-managed, clean-rerun, and fakeroot runs. Its direct dpkg case remains the outside-target negative control. The fixture cleanup path now canonicalizes and bounds recursive deletion before any `rm -rf`.

## Validation boundary

The candidate is checked by the shared Python suite, Perl syntax and POD checks, the current Debian sid `perltidy`, the explicit-TMPDIR regression, the full chrootless security fixture, and the expanded unwritable-TMPDIR review. Source lines before `__END__` remain within the repository's 79-column contract.

## Source boundary

- imported implementation: `upstream/mmdebstrap/mmdebstrap`
- original security work: PR #57
- defect: issue #69
- correction: PR #74
- retained patch: `0001-target-contained-tmpdir.patch`

No upstream contact is included or authorized.

## Limits

Chrootless mode is not a sandbox. A target directory can contain mount points or be modified concurrently by other actors with access to the same filesystem. This correction prevents the normal no-`TMPDIR` fallback and obvious final-component symlink escape; it does not claim race-free filesystem isolation against a hostile concurrent process.
