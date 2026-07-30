# How the mmdebstrap source test suite works

## In simple words

`mmdebstrap` does not have one small unit-test command. Its source suite prepares a local Debian mirror, expands 120 named shell-test templates into hundreds of distribution, mode, variant, and output-format cases, and runs them through local, privileged, or QEMU-backed environments.

A focused regression can finish in seconds. The complete suite is a much larger system exercise.

## What I learned

The main entry point is:

```sh
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh
```

`make_mirror.sh` prepares cached minimal Debian mirrors. After that cache exists, the suite is designed to run without an active internet connection for most tests.

`coverage.sh` performs source-quality checks before delegating to `coverage.py`. These include:

- an exact `perltidy` comparison;
- a maximum Perl code-line length of 79;
- Perl::Critic at severity 4;
- POD rendering;
- Python formatting checks;
- ShellCheck and `shfmt` checks.

The exact whole-file `perltidy` comparison depends on the formatter release used by the project. A newer formatter can rewrite untouched historical code, so formatter-version agreement is part of reproducing that check.

## Matrix expansion

`coverage.py` parses `coverage.txt`. Every test definition can select values from these dimensions:

- distributions: oldstable, stable, testing, unstable;
- modes: auto, root, unshare, fakechroot, chrootless;
- variants: extract, custom, essential, apt, minbase, buildd, `-`, standard;
- formats: auto, directory, tar, squashfs, ext2, ext4, null.

It forms the Cartesian product for the values named by each test and then applies skip expressions and environment requirements.

For imported revision `6fde999741f4fe1e7bf38079acf29432ef87a35e`, the inventory found:

- 120 test definitions;
- 120 matching test files;
- 3,501 lines across the test scripts;
- 283 generated cases before runtime filters;
- 274 potentially runnable cases on amd64 after static skip expressions;
- 45 definitions requiring root;
- 22 definitions requiring QEMU;
- 27 definitions requiring an isolated apt configuration.

The two largest expansions are:

- reproducible format-output comparison: 48 cases;
- tarball dry-run coverage: 40 cases.

## What “how long does it take?” means

There is no trustworthy single duration without naming the machine, mirror state, architecture, QEMU availability, formatter and coverage mode, and selected filters.

The cases vary widely:

- help and syntax checks are small;
- many cases create real Debian roots;
- format comparisons can build several artifacts;
- QEMU cases boot a virtual machine;
- enabling `Devel::Cover` adds substantial overhead.

`coverage.py` prints each case duration, estimated time remaining, slowest cases, and total runtime. That output is the proper way to answer the duration question for a particular environment.

The focused Linux Fieldwork deep review ran six TMPDIR behavior cases, static checks, and the suite inventory in roughly 34 seconds on a GitHub-hosted Ubuntu 24.04 runner. It did not run the 283-case source matrix.

## Running one test

The suite supports selecting one named test and narrowing dimensions. For example:

```sh
CMD=./mmdebstrap ./coverage.py \
  --dist unstable \
  --mode chrootless \
  fail-with-unwritable-tmpdir
```

This is the useful middle ground between a small standalone reproducer and the complete matrix.

## Source tests versus Debian autopkgtest

The source coverage suite and Debian autopkgtest answer different questions.

- The source suite exercises the repository's scenarios, modes, formats, and coverage goals.
- Debian autopkgtest checks the installed package in a Debian test environment and can be triggered by package or dependency changes.

Passing a focused source test does not replace either full source coverage or Debian autopkgtest. It provides strong evidence for one bounded behavior.

## Environment and assumptions

- Imported source revision: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Inventory architecture: amd64
- Inventory counts are generated from source configuration and do not include dynamic environment skips that only become known while running.

## Limits

The inventory counts cases; it does not predict runtime. The complete suite was not run in Linux Fieldwork, and no current upstream full-suite timing was available from a comparable public environment.

## Related work

- Related investigation: `../../investigations/mmdebstrap-unwritable-tmpdir/`
- Machine-readable inventory: `../../investigations/mmdebstrap-unwritable-tmpdir/results/suite-inventory.json`
- Source README: `../../upstream/mmdebstrap/README.md`
- Suite driver: `../../upstream/mmdebstrap/coverage.sh`
- Matrix runner: `../../upstream/mmdebstrap/coverage.py`
