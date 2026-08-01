# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Upstream base | `josch/mmdebstrap main@77ec9be5417ee44c96343d2347145585da1b1f94` |
| Exact current `tarfilter` blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Patched `tarfilter` blob | `a7bdcb73e574aa1720b319b8531f65d10fbd2446` |
| Proposed test blob | `9212cb89dfcb954d84d2f7f8e6557755d59e1986` |
| Patch SHA-256 | `8bdd156eb375114c3f3be80c4433a06f6ac8a6d8e189023a02d39774d80c2f74` |
| Local matrix SHA-256 | `f061350cf1e975dadad5e6e812ad0219cf664bfbfce6d4963e7459a45873a3b1` |
| Platform | Debian GNU/Linux 13.3, x86_64, kernel `6.12.13` |
| Runtime | Python `3.13.5`; GNU tar `1.35` |

## Exact-source identity

The 303-line current `tarfilter` was materialized from current public source chunks. `git hash-object tarfilter` returned:

```text
ad776167a8473d5d15dbe22e850f4f6db35cf278
```

This equals the public current-source blob.

## Baseline focused regression

### Command

```sh
# temporary directory containing exact current source as ./tarfilter
TERM=dumb ./tests/tarfilter-parent-metadata
```

### Observed result

```text
baseline_blob=ad776167a8473d5d15dbe22e850f4f6db35cf278
baseline_status=1
Traceback (most recent call last):
  File "<stdin>", line 10, in <module>
AssertionError: (['usr/bin/tool'], ['usr', 'usr/bin', 'usr/bin/tool'])
```

Failure owner: `tarfilter` parent-retention predicate.

## Candidate focused regression

### Commands

```sh
git apply --check patches/0001-tarfilter-retain-parent-metadata.patch
git apply patches/0001-tarfilter-retain-parent-metadata.patch
python3 -m py_compile tarfilter
sh -n tests/tarfilter-parent-metadata
TERM=dumb ./tests/tarfilter-parent-metadata
git diff --check
```

### Observed result

```text
candidate_status=0
patched_tarfilter_blob=a7bdcb73e574aa1720b319b8531f65d10fbd2446
proposed_test_blob=9212cb89dfcb954d84d2f7f8e6557755d59e1986
py_compile=PASS
shell_syntax=PASS
focused_five_case_test=PASS
git_diff_check=PASS
```

## Matrix

| Case | Baseline | Candidate | Evidence |
| --- | --- | --- | --- |
| Exact `/usr/bin/tool` | only leaf | both parents + leaf | focused test; matrix |
| Wildcard `/usr/*/tool` | parent relation broken | `usr` and `usr/bin` retained | focused test |
| Class `/usr/[bs]in/tool` | parent relation broken | chain retained | focused test |
| Boundary `/usr2/tool` | vulnerable to naive prefix fix | only `usr2` chain | focused test |
| Symlink `/linkroot/tool` | symlink omitted | symlink + leaf; target and metadata retained | focused test; matrix |
| Extracted parent modes | `0755`, `0755` | `0700`, `0711` | `artifacts/local-matrix.json` |
| Leading wildcard `*/tool` | conservative policy path | parent retained | relation matrix |
| Cleanup and immediate rerun | temporary files removed | repeated result matched | local execution |

## Patch application and rebase

- source hunk applied to exact current `tarfilter` blob with zero offset;
- proposed test is a new executable file;
- `coverage.txt` hunk uses exact current public context at line 78;
- local apply fixture retained only that context window, so `git apply --check` reported `offset -69 lines` for the registration hunk;
- this fixture offset does not establish full-file application;
- complete canonical checkout application remains pending;
- public overlap review completed 2026-08-01; recheck before submission.

## Upstream-native gates

| Gate | Command | Result |
| --- | --- | --- |
| Focused selector | `CMD=./mmdebstrap ./coverage.py tarfilter-parent-metadata` | PENDING FULL CHECKOUT |
| Black | `black --check ./tarfilter` | PENDING FULL CHECKOUT |
| Repository suite | `CMD=./mmdebstrap ./coverage.sh` or bounded maintainer-approved subset | PENDING MIRROR/CHECKOUT |
| Package/autopkgtest | project packaging command | PENDING |

## Linux Fieldwork retained gates

| Gate | Result | Artifact |
| --- | --- | --- |
| baseline/candidate archive matrix | PASS | `artifacts/local-matrix.json`, SHA-256 `f061350c…` |
| exact current source losing control | expected status 1 | `artifacts/exact-source-validation.txt` |
| exact patched source focused test | PASS | same receipt |
| Python compile | PASS | same receipt |
| shell syntax | PASS | same receipt |
| diff whitespace | PASS | same receipt |

## Cleanup and rerun

Temporary archive, extraction, and baseline-test directories were removed. No process, socket, mount, lock, container, cache entry, or host mutation remains. Durable packet artifacts are intentional retained state.

## Tests pending

- full canonical three-file patch application;
- native `coverage.py` selector;
- Black on the complete checkout;
- broader repository and package gates;
- hosted CI on an exact candidate branch.

## Final evidence statement

The exact current `tarfilter` source loses parent entries for the minimal include. The retained patch changes that exact source into a candidate that passes five focused cases and preserves directory and symlink metadata. Repository integration and project-native execution remain the first incomplete technical gate.
