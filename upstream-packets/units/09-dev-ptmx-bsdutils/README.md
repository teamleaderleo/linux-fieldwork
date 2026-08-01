# Unit 09 — mmdebstrap dev-ptmx declares bsdutils

## State

`ACTIVE`

This unit owns one package-test dependency correction: `tests/dev-ptmx` executes `script(1)` twice inside a generated apt-variant root, so that root must explicitly include `bsdutils`, the package providing `/usr/bin/script`.

## Exact identities

- Linux Fieldwork issue: `#397`, unit `09`
- Linux Fieldwork branch: `upstream/unit-09-dev-ptmx-bsdutils`
- Linux Fieldwork base: `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Internal packet validation PR: draft `#402`
- Superseded full-cache execution PR: closed `#403`
- Direct current-sid execution PR: draft `#407`
- Packet directory: `upstream-packets/units/09-dev-ptmx-bsdutils/`
- Imported source: `upstream/mmdebstrap/tests/dev-ptmx`, blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`
- Canonical upstream repository: `josch/mmdebstrap` on Muffin Forgejo
- Canonical upstream branch: `main`
- Canonical upstream head advertised during this work: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Canonical upstream source path: `tests/dev-ptmx`
- Controlled GitHub carrier: `teamleaderleo/mmdebstrap`
- Carrier provenance: downstream fork of `deepin-community/mmdebstrap`, both at `master` head `574048f2a720057b75e56622003932f344dc700a`
- Carrier base generation: `mmdebstrap 1.5.7-3`
- Carrier candidate branch: `linux-fieldwork/unit-09-dev-ptmx-bsdutils`
- Carrier candidate head: `43082a6bc959e2d7cefae48f52e045cc90869287`
- Carrier candidate blob: `fa93b4b845ff4927a72f258364bd920e8c7dc573`
- Direct execution branch: `investigation/mmdebstrap-dev-ptmx-direct-sid`
- Direct execution head: `cf33d8f3dc84cf1218a2cca859fc4db31e330bab`
- Direct workflow runs: `30691022149` for repository tests and `30691022161` for the named sid case; both queued at the latest checkpoint
- Intended final delivery: canonical Forgejo fork and pull request after authorization
- External-contact state: unauthorized; internal work only

## Historical owner

Recovered Debian CI run `72574145` tested `mmdebstrap 1.5.7-3` on Debian testing amd64. The suite passed 158 generated cases, skipped 93, then its first and only failure was `(252/283) dev-ptmx --mode=root --variant=apt`.

The generated root included:

```text
gcc,libc6-dev,python3,passwd
```

The test then attempted:

```text
chroot "$1" script -c "echo foobar"
```

and failed with:

```text
chroot: failed to run command ‘script’: No such file or directory
```

The failing archive carried `bsdutils 1:2.42.2-1`. `bsdutils` provides `/usr/bin/script`. The transition removed the former Essential-set assumption and exposed the undeclared test dependency.

## Candidate

The candidate changes one source line:

```diff
-  --include=gcc,libc6-dev,python3,passwd \
+  --include=bsdutils,gcc,libc6-dev,python3,passwd \
```

Retained upstream-path patch:

```text
patches/0001-tests-include-bsdutils-for-dev-ptmx.patch
```

Existing Linux Fieldwork evidence and regression remain canonical inputs:

- `investigations/mmdebstrap-dev-ptmx-bsdutils/0001-include-bsdutils.patch`
- `investigations/mmdebstrap-dev-ptmx-bsdutils/debci-72574145-summary.json`
- `tests/test_mmdebstrap_dev_ptmx_dependency.py`
- `tests/test_upstream_packet_unit_09_dev_ptmx_bsdutils.py`

## Current result

The controlled GitHub carrier base has the exact same `tests/dev-ptmx` blob as the Linux Fieldwork import: `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`. Candidate commit `43082a6bc959e2d7cefae48f52e045cc90869287` is one commit ahead of that base and changes exactly one file with one insertion and one deletion. Its resulting blob is `fa93b4b845ff4927a72f258364bd920e8c7dc573`.

The packet regression independently applies the upstream-rooted patch, requires both exact Git blob identities, rejects fuzz and offset, requires the one-line include delta, and preserves all customize hooks. Exact packet head `a4303b4bf3c02fb4acfc16337e53b68b08626862` passed Linux Fieldwork run `30690010699`.

PR `#403` retained useful carrier red controls but spent most of its execution budget building the complete package-test mirror. It is closed and superseded by PR `#407`.

PR `#407` starts from current Linux Fieldwork `main`, seeds only sid `InRelease`, uses `https://deb.debian.org/debian` directly, applies the exact candidate to a disposable source copy, and runs:

```text
coverage.py --exitfirst --mode=root --variant=apt dev-ptmx
```

with `/usr/bin/mmdebstrap`. It records package versions, baseline and candidate identities, rendered test output, residual mounts, residual files, and residual processes. The container is removed after execution.

The GitHub mirror survey found no copy containing canonical Forgejo commit `77ec9be5417ee44c96343d2347145585da1b1f94`. The newest inspected GitHub fork still carries baseline blob `ca1cde...` after unrelated local commits. GitHub timestamps therefore do not clear the canonical or mailing-list freshness gate.

## Next decision

Complete PR `#407` repository and direct-sid runs. On the first clean named-case pass, rerun the exact direct job immediately and compare artifacts. Then obtain canonical Forgejo `main`, inspect overlap and mailing-list-carried changes, and apply the one-line candidate with zero fuzz and zero offset. Equivalent canonical work retires the external submission; a clean absent correction moves the unit toward `READY FOR AUTHORIZATION`.
