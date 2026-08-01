# Tests

## Historical failing baseline

```text
Debian CI run: 72574145
package: mmdebstrap 1.5.7-3
case: (252/283) dev-ptmx --mode=root --variant=apt
root include set: gcc,libc6-dev,python3,passwd
failure: chroot: failed to run command ‘script’: No such file or directory
suite exit: 6
cleanup: generated root removed
```

This established the fixture owner: `tests/dev-ptmx` invokes `script(1)` inside its generated root and must select provider package `bsdutils`.

## Static Linux Fieldwork validation

```text
original PR: 89
original head: 9db9f4d9ae423a5c0dbd2255c05decf14fbe9d66
original workflow: 30539827917
packet head: a4303b4bf3c02fb4acfc16337e53b68b08626862
packet workflow: 30690010699
result: success
```

Validated properties:

- baseline blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`;
- Linux Fieldwork candidate blob `fa93b4b845ff4927a72f258364bd920e8c7dc573`;
- zero fuzz and zero offset;
- exactly one changed include line;
- two inner `script -c` hooks retained;
- complete customize-hook order retained.

The first packet run `30689859933` rejected a malformed hunk envelope before tests. It is a carrier-format red control with zero package claim.

## Controlled downstream fork

```text
repository: teamleaderleo/mmdebstrap
base head: 574048f2a720057b75e56622003932f344dc700a
base blob: ca1cde040f945fe871f904ef6a56e040b6a5c9ea
candidate commit: 43082a6bc959e2d7cefae48f52e045cc90869287
candidate blob: fa93b4b845ff4927a72f258364bd920e8c7dc573
compare: one commit, one file, +1/-1
```

The fork is a Deepin `1.5.7-3` carrier, not canonical history.

## Current-sid execution and rerun

Run `30690241513`:

```text
execution head: 501c19c7147b2452350069fda5375c4cdbc7ab7c
artifact: 8815599405
artifact digest: sha256:bd97c229b886501d57d4618381d1a07e446f48f6c46e409e1915f7d8675e0b82
root: SUCCESS, 18 seconds
unshare: SUCCESS, 18 seconds
```

Run `30690452822`:

```text
execution head: 55b603aa9a819217c19055a7becc91cf4832f082
artifact: 8815724078
artifact digest: sha256:897189064d42e06367ab652f590eb5827388dce8d883c042f079e49a7662273e
patch receipt: patching file tests/dev-ptmx
root: SUCCESS, 36 seconds
unshare: SUCCESS, 42 seconds
```

Across both runs:

- installed `mmdebstrap 1.5.7-3` and `bsdutils 1:2.42.2-2`;
- both inner `script` hooks printed `foobar`;
- copied logs had no missing-command signature;
- `/tmp/test.c` and `/tmp/log` were removed;
- every generated root was removed;
- selected testsuite result was `PASS`.

The outer autopkgtest status `2` came from unrelated skipped control entry `hint-testsuite-triggers`. See `artifacts/CURRENT-SID-DOUBLE-PASS.md`.

## Canonical Forgejo audit

```text
internal audit PR: 411
carrier head: 8c8b8a1753881b86f1d5628be659a98fbcc02c6f
workflow run: 30704384974
job: 91380861751
artifact: 8819850852
artifact digest: sha256:0504ab41ec727ffb87c5f803a6dc0611534ce0df0c0eadc2587a998808de9c2b
result: success
```

Exact findings:

```text
canonical main: 77ec9be5417ee44c96343d2347145585da1b1f94
main tests/dev-ptmx blob: ca1cde040f945fe871f904ef6a56e040b6a5c9ea
main include: gcc,libc6-dev,python3,passwd

canonical develop: 6e1e572bc49456daab7fd1274b1f3b8ec4a1c248
owning commit: c75b58e3c88b1f49626b9ee073e9e9688d38922c
corrected blob: 258a7f9579b2a2b91b6758952851296b44197ae0
develop include: gcc,libc6-dev,python3,passwd,bsdutils
corrected tag: 1.5.7+develop
```

The audit's first exact pickaxe searched only the Linux Fieldwork ordering and produced a false negative. Complete path history found the canonical appended ordering. Detailed evidence is in `artifacts/CANONICAL-FORGEJO-AUDIT.md`.

## Final disposition

- Historical ownership: proven.
- Minimal dependency semantics: proven.
- Static candidate: green.
- Current-sid execution and rerun: green.
- Cleanup: green.
- Canonical overlap: existing equivalent correction found.
- External submission: retired.

No further execution is required for unit 09.
