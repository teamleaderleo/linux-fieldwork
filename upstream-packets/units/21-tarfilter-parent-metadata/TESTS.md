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
| dpkg comparison script SHA-256 | `8d6132cc74cf43c42ed473c08f0d449e270c78d8ba480b2b2b5cd27fdb6aff4c` |
| dpkg comparison artifact SHA-256 | `65fbceebbb1b0dc7fdadcb13662dc039bc976adddb4989ee9dde4ba77281aa3b` |
| dpkg source file blob | `guillemj/dpkg main:src/main/filters.c@4fc1600a5717726faddc2fb556730f217e7f22a2` |
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

## dpkg compatibility comparison

### Command

```sh
python3 -m py_compile scripts/compare-dpkg-parent-retention.py
python3 scripts/compare-dpkg-parent-retention.py \
  > artifacts/dpkg-comparison.json
```

### Observed result

- status: `0`;
- eight assertions passed;
- exact nested ancestors: dpkg model `false`, candidate `true`;
- wildcard and leading-wildcard conservatism: both `true`;
- `/usr` or `/usr/*` against `/usr2`: dpkg model `true`, candidate `false`;
- unrelated path: both `false`;
- artifact: `artifacts/dpkg-comparison.json`, SHA-256 `65fbceeb…`.

The model is a direct transcription of the fixed-prefix calculation and `strncmp()` comparison in dpkg source blob `4fc1600…`. It is source-level evidence rather than a compiled dpkg integration test.

## Matrix

| Case | Baseline/reference | Candidate | Evidence |
| --- | --- | --- | --- |
| Exact `/usr/bin/tool` | exact current source emits only leaf | both parents + leaf | focused test; local matrix |
| Wildcard `/usr/*/tool` | current translated prefix broken | `usr` and `usr/bin` retained | focused test |
| Class `/usr/[bs]in/tool` | current translated prefix broken | chain retained | focused test |
| Boundary `/usr2/tool` | naive raw prefix can alias names | only `usr2` chain | focused test |
| Symlink `/linkroot/tool` | symlink omitted | symlink + leaf; target and metadata retained | focused test; local matrix |
| Extracted parent modes | `0755`, `0755` | `0700`, `0711` | `artifacts/local-matrix.json` |
| Exact ancestor versus dpkg | dpkg one-direction model drops parent | candidate retains parent | `artifacts/dpkg-comparison.json` |
| Wildcard conservatism versus dpkg | dpkg retains | candidate retains | same artifact |
| Sibling prefix `/usr`→`/usr2` | dpkg plain prefix retains | candidate rejects | same artifact |
| Leading wildcard `*/tool` | dpkg retains all candidates | candidate retains all candidates | same artifact |
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
| dpkg source-model comparison | PASS, eight cases | `artifacts/dpkg-comparison.json`, SHA-256 `65fbceeb…` |

## Cleanup and rerun

Temporary archive, extraction, baseline-test, comparison, and bytecode directories were removed. No process, socket, mount, lock, container, cache entry, or host mutation remains. Durable packet artifacts are intentional retained state.

## Tests pending

- full canonical three-file patch application;
- native `coverage.py` selector;
- Black on the complete checkout;
- broader repository and package gates;
- hosted CI on an exact candidate branch;
- compiled dpkg behavior comparison, only if maintainers request parity evidence.

## Final evidence statement

The exact current `tarfilter` source loses parent entries for the minimal include. The retained patch changes that exact source into a candidate that passes five focused cases and preserves directory and symlink metadata. The dpkg comparison establishes the deliberate compatibility boundary: preserve wildcard conservatism, add exact ancestry, and remove plain-prefix sibling aliases. Repository integration and project-native execution remain the first incomplete technical gate.
