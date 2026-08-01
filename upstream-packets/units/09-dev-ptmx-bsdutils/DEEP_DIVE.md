# Deep dive

## Mechanism

`tests/dev-ptmx` wraps the generated mmdebstrap invocation with host-side `script -qfec` to supply a pseudo-terminal. Inside the generated root, two customize hooks invoke `script(1)` again:

1. as root: `chroot "$1" script -c "echo foobar"`;
2. as the generated user: `chroot "$1" runuser -u user -- env --chdir=/home/user script -c "echo foobar"`.

The host-side `script` comes from the autopkgtest testbed. The two inner calls depend on packages selected into the generated apt-variant root.

The baseline include set is:

```text
gcc,libc6-dev,python3,passwd
```

`bsdutils` supplies `/usr/bin/script`. While `bsdutils` was Essential, the apt variant received it implicitly. In Debian testing with `bsdutils 1:2.42.2-1`, that guarantee disappeared. The fixture then failed before its intended PTY assertions could complete.

## Why the dependency belongs in the test

The test deliberately runs `script` inside the root. Explicitly naming the provider beside the existing root dependencies keeps the fixture independent from changes in Debian's Essential set. The correction expresses the command-level requirement where the root is constructed.

## Candidate properties

- adds exactly one package name;
- preserves the existing package order after the new provider;
- preserves all customize hooks and their order;
- changes no product runtime code;
- changes no Debian package metadata;
- changes no host-side testbed dependency;
- remains valid whether `bsdutils` is Essential or ordinary.

## Controlled GitHub carrier provenance

The user-controlled repository `teamleaderleo/mmdebstrap` is a GitHub fork of `deepin-community/mmdebstrap`, not a mirror of canonical Forgejo ancestry. Both repositories identify `master` head `574048f2a720057b75e56622003932f344dc700a` with subject `feat: update mmdebstrap to 1.5.7-3`.

Its `tests/dev-ptmx` blob is `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`, byte-identical to the Linux Fieldwork import. The controlled candidate branch changes that file to blob `fa93b4b845ff4927a72f258364bd920e8c7dc573` at commit `43082a6bc959e2d7cefae48f52e045cc90869287`.

This carrier proves exact application to the source generation that produced the historical Debian failure. Debian sid still carries `mmdebstrap 1.5.7-3`, so it also provides a valid current-package execution base. Its history cannot prove inclusion of later Forgejo, Salsa, Debian-series, or mailing-list patches.

## GitHub mirror survey

Accessible GitHub repositories do not contain advertised canonical commit `77ec9be5417ee44c96343d2347145585da1b1f94`.

The newest inspected fork, `RubisetCie/mmdebstrap`, carries two unrelated local commits after the same Deepin base and still has baseline `dev-ptmx` blob `ca1cde...`. A newer GitHub timestamp therefore cannot establish canonical freshness.

Public indexed searches found no equivalent `dev-ptmx`/`bsdutils` correction in the canonical tracker, Debian BTS, or Debian mailing-list archives. Search coverage remains incomplete; exact canonical history is decisive.

## Packet-carrier failure and repair

The first internal PR `#402` run rejected the retained email-style patch before tests:

```text
invalid hunk-body prefix '2'
hunk count mismatch: declared old/new 8/8, observed 8/7
```

The source candidate was unaffected. The packet carrier was replaced with the exact pure unified diff from controlled-fork commit `43082a6bc959e2d7cefae48f52e045cc90869287`, using a `7/7` hunk and no trailer.

Exact packet head `a4303b4bf3c02fb4acfc16337e53b68b08626862` then passed run `30690010699`: patch validation, compilation, the complete repository unit suite, shell syntax, and command-help checks.

## Dynamic current-sid result

Two separate disposable Debian sid runs executed installed `mmdebstrap 1.5.7-3` with `bsdutils 1:2.42.2-2` and the candidate source line.

Run `30690241513`:

```text
root:    SUCCESS, 18 seconds
unshare: SUCCESS, 18 seconds
```

Run `30690452822`, with the unit patch applied independently under the zero-fuzz/zero-offset contract:

```text
root:    SUCCESS, 36 seconds
unshare: SUCCESS, 42 seconds
```

Across both runs:

- both inner `script -c` hooks printed `foobar`;
- copied apt logs contained no missing-command signature;
- `/tmp/test.c` and `/tmp/log` were removed;
- mmdebstrap removed every generated root;
- the selected testsuite result was `PASS`.

The outer autopkgtest status `2` came from the unrelated skipped `hint-testsuite-triggers` control entry. The named package-test result passed twice.

The complete receipt is `artifacts/CURRENT-SID-DOUBLE-PASS.md`.

## Execution-carrier lessons

PR `#403` established two useful boundaries:

1. a focus hunk applied before other testsuite transformations conflicts with the capability patch;
2. bundling the independent `dev-ptmx` source correction into the installed-command wrapper patch violates fixture ownership.

The cleaner composition applies the unit patch as its own exact carrier after unrelated compatibility patches. PR `#403` is closed because the full cache phase was excessive for one dependency case.

Draft PR `#407` is an optional direct lane. It seeds only sid `InRelease`, uses the public Debian mirror, selects `coverage.py --exitfirst --mode=root --variant=apt dev-ptmx`, and records residual mounts, files, and processes. The double-pass evidence already completes the required dynamic gate.

## Approaches rejected

### Change util-linux packaging

Rejected. The test owns an undeclared command dependency. Restoring Essential status would broaden the intervention and preserve the fixture's implicit package-set coupling.

### Replace `script` with another PTY helper

Rejected. The case intentionally exercises PTY behavior through `script`; replacement would alter the test's intent.

### Install `bsdutils` in autopkgtest control dependencies only

Rejected. Host-side availability already existed. The missing binary was inside the generated root.

### Add a runtime dependency to mmdebstrap

Rejected. mmdebstrap itself does not require `script` for ordinary operation. The dependency belongs solely to this test fixture.

### Treat Deepin GitHub history as canonical upstream

Rejected. Its exact source bytes are useful for Debian `1.5.7-3` execution, while its ancestry differs from canonical Forgejo `main`.

### Fold unrelated current-sid harness fixes into this candidate

Rejected. Phase ordering, wrappers, signals, and observability have separate owners. The upstream candidate remains one dependency-line edit.

## Compatibility analysis

`bsdutils` remains the direct provider of `/usr/bin/script`. Adding it explicitly is harmless on releases where apt would already select it and necessary where it is ordinary. Current sid dynamic execution confirms the candidate with `bsdutils 1:2.42.2-2`.

## Hold discriminator

The technical correction, static validation, current-sid pass, cleanup, and immediate rerun are complete.

The single unresolved question is canonical source state:

1. fetch Forgejo `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`, or a fresher verified head;
2. inspect `tests/dev-ptmx` history and mailing-list-carried overlap;
3. apply the packet patch with zero fuzz and zero offset.

Outcomes:

- equivalent correction present: retire the external submission;
- dependency absent and patch applies cleanly: prepare the canonical fork branch and move to `READY FOR AUTHORIZATION`;
- changed test intent or provider: reopen ownership analysis.
