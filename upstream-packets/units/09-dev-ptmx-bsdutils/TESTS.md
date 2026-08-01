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

The original regression command is:

```sh
python3 -m unittest tests.test_mmdebstrap_dev_ptmx_dependency
```

## Controlled GitHub carrier application

### Base

```text
repository: teamleaderleo/mmdebstrap
provenance: deepin-community/mmdebstrap downstream fork
branch: master
head: 574048f2a720057b75e56622003932f344dc700a
commit subject: feat: update mmdebstrap to 1.5.7-3
tests/dev-ptmx blob: ca1cde040f945fe871f904ef6a56e040b6a5c9ea
include: gcc,libc6-dev,python3,passwd
inner script hooks: 2
```

The base head and repository metadata match `deepin-community/mmdebstrap`; this is downstream packaging history rather than canonical Forgejo ancestry.

### Candidate

```text
branch: linux-fieldwork/unit-09-dev-ptmx-bsdutils
head: 43082a6bc959e2d7cefae48f52e045cc90869287
tests/dev-ptmx blob: fa93b4b845ff4927a72f258364bd920e8c7dc573
compare: ahead 1, behind 0, one file, +1/-1
pull request: none
```

Exact commit diff:

```diff
-	--include=gcc,libc6-dev,python3,passwd \
+	--include=bsdutils,gcc,libc6-dev,python3,passwd \
```

GitHub content verification confirmed the candidate retains both inner `script -c` hooks and all surrounding hook order.

## Packet/fork regression

Committed test:

```text
tests/test_upstream_packet_unit_09_dev_ptmx_bsdutils.py
introducing commit: aaf0d1706b5aa858a08b454d8c92003dd2188c7e
internal draft PR: #402
```

Command:

```sh
python3 -m unittest -v \
  tests.test_upstream_packet_unit_09_dev_ptmx_bsdutils
```

Contract:

- compute the Git blob SHA of the imported baseline and require `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`;
- require the packet patch to target `tests/dev-ptmx`, not the Linux Fieldwork import prefix;
- apply the packet patch to a fresh temporary upstream-shaped tree;
- reject patch output containing fuzz or offset;
- compute the candidate Git blob SHA and require `fa93b4b845ff4927a72f258364bd920e8c7dc573`;
- require exactly one changed source line at line 122;
- require the complete include list `bsdutils,gcc,libc6-dev,python3,passwd`;
- require both inner `script -c` hooks and all customize hooks to remain in the original order;
- remove each temporary directory through `TemporaryDirectory` cleanup.

CI state: draft PR `#402` opened to execute Linux Fieldwork CI. Record the final exact workflow head and result after the latest packet commit settles.

## Current Debian source relevance

Debian sid currently carries source package `mmdebstrap 1.5.7-3`. Unit 08 identifies the exact Debian executable base as tag `debian/1.5.7-3`, commit `6fde999741f4fe1e7bf38079acf29432ef87a35e`. The controlled GitHub carrier is therefore relevant to a current-sid package execution of this specific one-line correction.

The carrier cannot establish canonical Forgejo freshness. Missing canonical-main or mailing-list patches remain an overlap/rebase concern before final upstream delivery.

## Canonical network checkout attempts

Commands attempted in this execution environment:

```sh
git ls-remote https://gitlab.mister-muffin.de/josch/mmdebstrap.git refs/heads/main
git clone --no-tags --single-branch --branch master \
  https://github.com/teamleaderleo/mmdebstrap.git /tmp/unit09-mmdebstrap
```

Results:

```text
Could not resolve host: gitlab.mister-muffin.de
Could not resolve host: github.com
```

The connected GitHub API remained available. The official canonical repository page remained readable and advertised `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`.

## Unexecuted gates

### Canonical current-head application and overlap review

Obtain exact canonical Forgejo bytes at `77ec9be5417ee44c96343d2347145585da1b1f94` or a fresher verified `main`, inspect `tests/dev-ptmx` history and mailing-list-carried overlap, then apply the packet patch with zero fuzz and zero offset.

Expected: one changed include line, or retirement if equivalent work already landed.

### Focused current-sid run

Use the unit-08 disposable package-test carrier or its successor. Apply the candidate to the temporary Debian `1.5.7-3` source copy and select:

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

Historical ownership, prior static validation, controlled-fork application, exact one-file compare, and candidate blob verification are complete. Draft PR `#402` CI, canonical-current overlap review, current-sid named execution, cleanup verification, and immediate rerun remain open.
