# Unit 09 — mmdebstrap dev-ptmx declares bsdutils

## State

`HOLD`

Single blocker: exact canonical Forgejo `main` bytes and history, including mailing-list-carried overlap, remain unavailable in this execution environment.

This unit owns one package-test dependency correction: `tests/dev-ptmx` executes `script(1)` twice inside a generated apt-variant root, so that root must explicitly include `bsdutils`, the package providing `/usr/bin/script`.

## Exact identities

- Linux Fieldwork issue: `#397`, unit `09`
- Linux Fieldwork branch: `upstream/unit-09-dev-ptmx-bsdutils`
- Linux Fieldwork base: `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Packet directory: `upstream-packets/units/09-dev-ptmx-bsdutils/`
- Internal packet validation PR: draft `#402`
- Superseded full-cache execution PR: closed `#403`
- Optional direct current-sid execution PR: draft `#407`
- Imported source: `upstream/mmdebstrap/tests/dev-ptmx`, blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`
- Canonical repository: `josch/mmdebstrap` on Muffin Forgejo
- Canonical branch: `main`
- Advertised canonical head: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Canonical source path: `tests/dev-ptmx`
- Controlled GitHub carrier: `teamleaderleo/mmdebstrap`
- Carrier provenance: fork of `deepin-community/mmdebstrap`
- Carrier base: `master` at `574048f2a720057b75e56622003932f344dc700a`
- Carrier candidate branch: `linux-fieldwork/unit-09-dev-ptmx-bsdutils`
- Carrier candidate head: `43082a6bc959e2d7cefae48f52e045cc90869287`
- Carrier candidate blob: `fa93b4b845ff4927a72f258364bd920e8c7dc573`
- Optional direct execution branch: `investigation/mmdebstrap-dev-ptmx-direct-sid`
- Optional direct execution head: `ff573bdd4ce1c822fad47218bff052fcc87126a4`
- External-contact state: unauthorized; internal work only

## Historical owner

Recovered Debian CI run `72574145` tested `mmdebstrap 1.5.7-3` on Debian testing amd64. The suite passed 158 generated cases, skipped 93, then its first and only failure was `(252/283) dev-ptmx --mode=root --variant=apt`.

The generated root included:

```text
gcc,libc6-dev,python3,passwd
```

The test attempted:

```text
chroot "$1" script -c "echo foobar"
```

and failed with:

```text
chroot: failed to run command ‘script’: No such file or directory
```

The failing archive carried `bsdutils 1:2.42.2-1`. `bsdutils` provides `/usr/bin/script`. The Essential-set transition exposed the undeclared test dependency.

## Candidate

```diff
-  --include=gcc,libc6-dev,python3,passwd \
+  --include=bsdutils,gcc,libc6-dev,python3,passwd \
```

Retained upstream-rooted patch:

```text
patches/0001-tests-include-bsdutils-for-dev-ptmx.patch
```

Durable evidence and regressions:

- `investigations/mmdebstrap-dev-ptmx-bsdutils/0001-include-bsdutils.patch`
- `investigations/mmdebstrap-dev-ptmx-bsdutils/debci-72574145-summary.json`
- `tests/test_mmdebstrap_dev_ptmx_dependency.py`
- `tests/test_upstream_packet_unit_09_dev_ptmx_bsdutils.py`
- `artifacts/CURRENT-SID-DOUBLE-PASS.md`

## Completed validation

### Static

Exact packet head `a4303b4bf3c02fb4acfc16337e53b68b08626862` passed Linux Fieldwork run `30690010699`:

- valid changed patch carrier;
- Python compilation;
- complete repository unit suite;
- shell syntax and command-help checks.

The regression requires exact baseline and candidate Git blob identities, zero fuzz and zero offset, one changed line, and unchanged customize-hook order.

### Controlled fork

The controlled fork base has the exact imported source blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`. Candidate commit `43082a6bc959e2d7cefae48f52e045cc90869287` is one commit ahead and changes one file with one insertion and one deletion. The candidate blob is `fa93b4b845ff4927a72f258364bd920e8c7dc573`.

### Current sid: pass and rerun

Two separate disposable Debian sid containers passed both generated variants with installed `mmdebstrap 1.5.7-3` and `bsdutils 1:2.42.2-2`.

Run `30690241513`:

```text
root:    SUCCESS, 18 seconds
unshare: SUCCESS, 18 seconds
artifact: 8815599405
sha256:bd97c229b886501d57d4618381d1a07e446f48f6c46e409e1915f7d8675e0b82
```

Run `30690452822`, preferred exact application receipt:

```text
root:    SUCCESS, 36 seconds
unshare: SUCCESS, 42 seconds
artifact: 8815724078
sha256:897189064d42e06367ab652f590eb5827388dce8d883c042f079e49a7662273e
```

Across both runs:

- both inner `script -c` hooks printed `foobar`;
- copied apt logs contained no missing-command signature;
- `/tmp/test.c` and `/tmp/log` were removed;
- mmdebstrap removed every generated root;
- the selected testsuite result was `PASS`.

The outer autopkgtest status `2` came from the unrelated skipped `hint-testsuite-triggers` entry.

## Fork and mailing-list freshness

The user's GitHub repository is a useful Debian `1.5.7-3` implementation carrier. Its history follows the Deepin downstream import. A survey of accessible GitHub repositories found no mirror containing canonical commit `77ec9be5417ee44c96343d2347145585da1b1f94`; newer GitHub timestamps represented local divergence while retaining the same baseline `dev-ptmx` blob.

Public indexed searches found no equivalent correction in the canonical tracker, Debian BTS, or Debian mailing-list archives. Exact canonical bytes and history remain the decisive evidence.

## Hold discriminator

Fetch canonical Forgejo `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`, or a fresher verified head, then inspect `tests/dev-ptmx` history and mailing-list overlap and apply the packet patch with zero fuzz and zero offset.

- Equivalent correction present: retire the external submission.
- Dependency absent and patch applies cleanly: prepare a canonical fork branch and move to `READY FOR AUTHORIZATION`.
- Test intent changed: reopen ownership analysis.

Draft PR `#407` is optional supporting confirmation with explicit residual mount/file/process checks. At this checkpoint its latest runs were queued:

```text
Linux Fieldwork CI:           30691203697
Direct current-sid execution: 30691203699
```

## Authority

No mmdebstrap or Debian upstream issue, pull request, comment, email, review, or other contact was created. External delivery requires explicit authorization.
