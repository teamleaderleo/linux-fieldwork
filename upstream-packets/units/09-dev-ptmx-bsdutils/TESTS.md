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

### Packet-carrier red control

Run `30689859933` rejected the first retained patch before tests:

```text
invalid hunk-body prefix '2'
hunk count mismatch: declared old/new 8/8, observed 8/7
```

Classification: packet-format failure, zero package claim. The carrier was replaced with a pure count-correct unified diff.

### Exact static success

```text
unit head: a4303b4bf3c02fb4acfc16337e53b68b08626862
workflow run: 30690010699
changed patch validation: success
Python compilation: success
complete repository unit suite: success
shell syntax and command help: success
privileged package jobs: correctly skipped
```

This is the current authoritative static result for the packet branch before adding the execution receipts below.

## Focused current-sid execution carrier

Internal draft PR `#403` uses the proven disposable Debian sid carrier from PR `#361` and exits after `coverage.py --exitfirst dev-ptmx`. It changes only the temporary imported source and contacts no external project.

### Attempt 1 — focus hunk conflict

```text
workflow run: 30690124748
execution head: 8fa7ea7e857ac966c0473468178a460731a485db
artifact ID: 8815363717
artifact digest: sha256:b52556a4a6735e553daf5daf01d865d8ef68edad9f9ec3b448c699e8cc4432d3
classification: carrier-preflight-failure
package claim: zero
```

Exact patch output:

```text
patching file debian/tests/testsuite
Hunk #2 FAILED at 189.
1 out of 2 hunks FAILED
patching file tests/dev-ptmx
```

The unit-09 source hunk applied. The focus edit conflicted with the capability patch that had already changed the testsuite. The focus transformation moved into an environment-gated post-patch tool.

### Attempt 2 — bundled patch breaks repository fixtures

```text
workflow run: 30690241513
execution head: 501c19c7147b2452350069fda5375c4cdbc7ab7c
BTS capture: success
focused sid container: in progress when this receipt was written
lab-tools: failure
```

The sid carrier crossed patch preflight and entered real package work. The repository suite found four fixture failures because `installed-command-wrapper.patch` had been expanded to include `tests/dev-ptmx`, while established wrapper tests intentionally construct a fixture containing only `debian/tests/testsuite`.

Exact failure boundary:

```text
can't find file to patch at input line 48
diff --git a/tests/dev-ptmx b/tests/dev-ptmx
No file to patch. Skipping patch.
```

Classification: carrier composition defect. The unit-09 source candidate remains unchanged.

### Attempt 3 — independent exact patch carrier

```text
execution head: 55b603aa9a819217c19055a7becc91cf4832f082
workflow run: 30690452822
status at receipt: queued behind attempt 2
```

Repair:

- restore `installed-command-wrapper.patch` to its proven testsuite-only bytes;
- apply `dev-ptmx-bsdutils-source.patch` as a fifth independent exact patch;
- retain zero-fuzz/zero-offset receipts for every patch;
- set `UNIT09_FOCUS=dev-ptmx` only in PR `#403`;
- transform the already-composed testsuite after all patches;
- run only the named case and exit before unrelated phases.

Attempt 3 must produce both a green repository suite and a focused sid result on the same exact head before it becomes authoritative.

## Current Debian source relevance

Debian sid carries the `mmdebstrap 1.5.7` source generation. Unit 08 identifies the exact Debian executable base as tag `debian/1.5.7-3`, commit `6fde999741f4fe1e7bf38079acf29432ef87a35e`. The controlled GitHub carrier is therefore relevant to current-sid package execution of this one-line correction.

The carrier cannot establish canonical Forgejo freshness. Missing canonical-main or mailing-list patches remain an overlap/rebase concern before final upstream delivery.

## Canonical and mailing-list overlap search

Public indexed searches for `dev-ptmx`, `bsdutils`, and the exact corrected include line found no equivalent canonical issue, pull request, Debian BTS item, or mailing-list result. The official canonical page advertises `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`.

Search absence is supporting evidence only. Exact canonical bytes and history remain the final overlap gate.

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

The connected GitHub API remained available. The official canonical repository page remained readable.

## Remaining gates

### Authoritative focused current-sid pass

Complete PR `#403` run `30690452822` or its exact successor. Record mirror identity, package universe, candidate commit, command, exit status, artifact ID and digest, named result, and cleanup state.

### Cleanup and immediate rerun

After the first focused pass:

- verify the generated root is removed;
- verify no listener, mount, container, or temporary source tree survives;
- rerun the exact candidate and command;
- compare result and first-result coordinates.

### Canonical current-head application and overlap review

Obtain exact canonical Forgejo bytes at `77ec9be5417ee44c96343d2347145585da1b1f94` or a fresher verified `main`, inspect `tests/dev-ptmx` history and mailing-list-carried overlap, then apply the packet patch with zero fuzz and zero offset.

Expected: one changed include line, or retirement if equivalent work already landed.

## Current test disposition

Historical ownership, prior static validation, controlled-fork application, exact one-file compare, candidate blob verification, and packet-branch CI are complete. The authoritative focused sid pass, cleanup verification, immediate rerun, and canonical-current overlap review remain open.
