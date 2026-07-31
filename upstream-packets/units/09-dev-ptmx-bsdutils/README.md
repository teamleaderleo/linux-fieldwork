# Unit 09 — mmdebstrap dev-ptmx declares bsdutils

## State

`ACTIVE`

This unit owns one package-test dependency correction: `tests/dev-ptmx` executes `script(1)` twice inside a generated apt-variant root, so that root must explicitly include `bsdutils`, the package providing `/usr/bin/script`.

## Exact identities

- Linux Fieldwork issue: `#397`, unit `09`
- Linux Fieldwork branch: `upstream/unit-09-dev-ptmx-bsdutils`
- Linux Fieldwork base: `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Packet directory: `upstream-packets/units/09-dev-ptmx-bsdutils/`
- Imported source: `upstream/mmdebstrap/tests/dev-ptmx`, blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`
- Canonical upstream repository: `josch/mmdebstrap` on Muffin Forgejo
- Upstream branch: `main`
- Upstream head advertised during this pass: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Upstream source path: `tests/dev-ptmx`
- Controlled upstream fork: `NEEDS FORK`
- Intended delivery: Forgejo fork and pull request
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

## Current result

The imported current source still has the baseline include line at source line 122 and retains exactly two inner `script -c` customize hooks. PR `#89` previously validated the same one-line candidate at exact head `9db9f4d9ae423a5c0dbd2255c05decf14fbe9d66`; Linux Fieldwork CI run `30539827917` passed.

Direct network checkout of the canonical upstream repository failed in this execution environment because DNS resolution for `gitlab.mister-muffin.de` was unavailable. The official repository page was readable and advertised the upstream head above. Exact raw-byte application to that upstream commit and the current-sid named package-test execution remain open gates.

## Next decision

Fetch or fork exact upstream head `77ec9be5417ee44c96343d2347145585da1b1f94`, apply the retained upstream-path patch with zero fuzz and zero offset, run the focused static assertions, then run `dev-ptmx --mode=root --variant=apt` through the reusable disposable sid harness with cleanup and immediate rerun.
