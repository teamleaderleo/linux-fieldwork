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
| Cleanup | generated root cleanup completed |

## Existing candidate validation

PR `#89`, exact head `9db9f4d9ae423a5c0dbd2255c05decf14fbe9d66`:

```text
Linux Fieldwork CI run 30539827917: success
```

Validated contract:

- baseline contains two inner `script -c` hooks;
- baseline include line omits `bsdutils`;
- retained patch applies to an exact temporary copy;
- candidate include line is `bsdutils,gcc,libc6-dev,python3,passwd`;
- exactly one source line changes;
- customize-hook order remains byte-for-byte unchanged;
- evidence fixture names run, case, missing command, provider package, and binary path.

The regression command used by the repository is:

```sh
python3 -m unittest tests.test_mmdebstrap_dev_ptmx_dependency
```

## Current-pass source observation

Linux Fieldwork `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`:

```text
upstream/mmdebstrap/tests/dev-ptmx blob ca1cde040f945fe871f904ef6a56e040b6a5c9ea
line 122: --include=gcc,libc6-dev,python3,passwd
inner script hooks: 2
```

The packet patch preserves the candidate as an upstream-rooted diff under `patches/`.

## Network checkout attempt

Command:

```sh
git ls-remote https://gitlab.mister-muffin.de/josch/mmdebstrap.git refs/heads/main
```

Result:

```text
fatal: unable to access 'https://gitlab.mister-muffin.de/josch/mmdebstrap.git/': Could not resolve host: gitlab.mister-muffin.de
```

The official repository page remained readable through the research tool and advertised `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`.

## Unexecuted gates

### Exact upstream application

```sh
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap.git
cd mmdebstrap
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git apply --check ../0001-tests-include-bsdutils-for-dev-ptmx.patch
git apply ../0001-tests-include-bsdutils-for-dev-ptmx.patch
git diff --check
git diff -- tests/dev-ptmx
```

Expected: zero fuzz, zero offset, one changed include line.

### Focused current-sid run

Use the disposable package-test carrier from PR `#72` or its current successor, with the candidate applied only to the temporary upstream source copy. Select:

```text
dev-ptmx
mode=root
variant=apt
dist=unstable or current sid
```

Record exact mirror identity, package universe, candidate commit, command, exit status, retained artifact digest, first failure or success line, and cleanup result.

### Cleanup and immediate rerun

After the first focused run:

- verify the generated root is removed;
- verify no listener, mount, container, or temporary source tree survives;
- rerun the exact candidate and command;
- compare result and first-failure coordinates.

## Current test disposition

Historical ownership and static candidate validation are green. Exact current-upstream application, current-sid named execution, cleanup verification, and immediate rerun remain open.
