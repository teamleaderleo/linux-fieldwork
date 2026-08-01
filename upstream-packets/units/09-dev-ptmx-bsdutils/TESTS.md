# Tests

## Historical baseline

| Field | Result |
| --- | --- |
| Debian CI run | `72574145` |
| Package | `mmdebstrap 1.5.7-3` |
| Testbed | Debian testing amd64 |
| Trigger | `migration-reference%2F0` |
| Case | `(252/283) dev-ptmx --mode=root --variant=apt` |
| Passed before failure | `158` |
| Skipped | `93` |
| Suite exit | `6` |
| Root include set | `gcc,libc6-dev,python3,passwd` |
| First unavailable command | `chroot "$1" script -c "echo foobar"` |
| Failure | `chroot: failed to run command ‘script’: No such file or directory` |
| Cleanup | generated root removed |

The historical transcript proves ownership: the generated root executed `script(1)` without selecting provider package `bsdutils`.

## Static candidate validation

### Original focused regression

PR `#89`, exact head `9db9f4d9ae423a5c0dbd2255c05decf14fbe9d66`:

```text
Linux Fieldwork CI run 30539827917: success
```

The regression proves the baseline omission, exact patch application, one changed source line, complete include list, unchanged customize-hook order, and historical provider evidence.

### Packet and controlled-fork regression

```text
test: tests/test_upstream_packet_unit_09_dev_ptmx_bsdutils.py
packet head: a4303b4bf3c02fb4acfc16337e53b68b08626862
workflow run: 30690010699
result: success
```

Passed gates:

- changed patch validation;
- Python compilation;
- complete repository unit suite;
- shell syntax and command-help checks.

Exact identities asserted:

```text
baseline blob:  ca1cde040f945fe871f904ef6a56e040b6a5c9ea
candidate blob: fa93b4b845ff4927a72f258364bd920e8c7dc573
```

The packet patch applies to a temporary upstream-rooted tree with zero fuzz and zero offset, changes only line 122, and preserves every customize hook in order.

### Packet-format red control

Run `30689859933` rejected the first retained email-style patch before tests:

```text
invalid hunk-body prefix '2'
hunk count mismatch: declared old/new 8/8, observed 8/7
```

Classification: packet-format failure with zero package claim. The retained carrier was replaced with a pure count-correct unified diff.

## Controlled GitHub carrier

```text
repository: teamleaderleo/mmdebstrap
provenance: fork of deepin-community/mmdebstrap
base branch: master
base head: 574048f2a720057b75e56622003932f344dc700a
base blob: ca1cde040f945fe871f904ef6a56e040b6a5c9ea
candidate branch: linux-fieldwork/unit-09-dev-ptmx-bsdutils
candidate head: 43082a6bc959e2d7cefae48f52e045cc90869287
candidate blob: fa93b4b845ff4927a72f258364bd920e8c7dc573
compare: one commit, one file, one insertion, one deletion
pull request: none
```

This carrier matches the Debian `1.5.7-3` source generation byte-for-byte. Its Deepin ancestry does not establish canonical Forgejo freshness.

## Current-sid dynamic confirmation and rerun

Durable compact receipt:

```text
artifacts/CURRENT-SID-DOUBLE-PASS.md
```

Both disposable Debian sid executions used installed `mmdebstrap 1.5.7-3`, `bsdutils 1:2.42.2-2`, apt `3.3.2`, and the candidate include list:

```text
bsdutils,gcc,libc6-dev,python3,passwd
```

### Run 30690241513

```text
execution head: 501c19c7147b2452350069fda5375c4cdbc7ab7c
artifact ID: 8815599405
artifact digest: sha256:bd97c229b886501d57d4618381d1a07e446f48f6c46e409e1915f7d8675e0b82
console digest: sha256:a492438a91a79f85d85fe80bdd8a88cbec685c1c6f55b9ceb7b7bf36369fcd5c
```

Named results:

```text
(253/284) dev-ptmx --mode=root:    SUCCESS, 0:00:18
(254/284) dev-ptmx --mode=unshare: SUCCESS, 0:00:18
successfully ran 2 tests
```

### Run 30690452822

This is the preferred application receipt because the unit patch applied as an independent fifth patch under the zero-fuzz/zero-offset contract.

```text
execution head: 55b603aa9a819217c19055a7becc91cf4832f082
artifact ID: 8815724078
artifact digest: sha256:897189064d42e06367ab652f590eb5827388dce8d883c042f079e49a7662273e
console digest: sha256:d9ec564c256c02717a1de24d7a776e98a57ac104d016363d9f35ebd11d2d5c0f
patch receipt: patching file tests/dev-ptmx
```

Named results:

```text
(253/284) dev-ptmx --mode=root:    SUCCESS, 0:00:36
(254/284) dev-ptmx --mode=unshare: SUCCESS, 0:00:42
successfully ran 2 tests
```

Across both runs:

- both inner `script -c` hooks printed `foobar`;
- copied apt logs contained no missing-command signature;
- `/tmp/test.c` and `/tmp/log` were removed;
- mmdebstrap removed every generated temporary root;
- the testsuite result was `PASS`.

The outer autopkgtest status was `2` because the unrelated control entry `hint-testsuite-triggers` was classified as `SKIP`; the selected `testsuite` entry passed.

## Superseded full-cache carrier

Internal PR `#403` is closed. It retained useful preflight controls and produced the two positive artifacts above, but spent most of its runtime building the complete package-test mirror.

## Optional direct one-case carrier

Draft PR `#407` starts from Linux Fieldwork `main`, seeds sid `InRelease`, uses `https://deb.debian.org/debian`, applies the exact candidate to a disposable source copy, and selects only:

```text
coverage.py --exitfirst --mode=root --variant=apt dev-ptmx
```

Latest exact direct branch head:

```text
ff573bdd4ce1c822fad47218bff052fcc87126a4
```

Latest queued runs at this checkpoint:

```text
Linux Fieldwork CI:             30691203697
Unit 09 direct sid execution:   30691203699
```

This lane adds explicit residual mount, file, and process checks and seeks a zero-status wrapper. It is useful supporting confirmation and is not a prerequisite for the ownership or current-sid pass conclusions.

## Canonical and mailing-list overlap review

Public indexed searches found no equivalent `dev-ptmx`/`bsdutils` correction in the canonical tracker, Debian BTS, or Debian mailing-list archives. Accessible GitHub repositories also retain the baseline blob and do not contain advertised canonical commit `77ec9be5417ee44c96343d2347145585da1b1f94`.

Search absence cannot prove canonical absence. Exact Forgejo bytes and history remain required before external delivery.

## Remaining required gate

Obtain canonical Forgejo `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`, or a fresher verified head, then:

1. inspect `tests/dev-ptmx` history and mailing-list-carried overlap;
2. apply the packet patch with zero fuzz and zero offset;
3. record the canonical base and candidate identities.

Disposition:

- equivalent correction present: retire the external submission;
- dependency absent and patch applies cleanly: move toward `READY FOR AUTHORIZATION`;
- changed test intent: reopen ownership analysis.

## Current test disposition

Historical ownership, static validation, controlled-fork application, current-sid execution, cleanup within the named tests, and immediate rerun are complete. Canonical Forgejo byte/history review is the sole required blocker. PR `#407` is optional supporting confirmation.
