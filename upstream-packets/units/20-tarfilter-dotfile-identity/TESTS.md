# Tests

## Evidence policy

The retained earlier receipts prove the original narrow defect and an earlier candidate revision. The current 249-line test and repaired helper supersede them for final disposition. The authoritative final gate is the exact-head workflow on the final branch tip.

A direct green invocation alone does not satisfy the unit stop rule.

## Environments used during the deeper pass

Local discriminator environment:

```text
Python 3.13.5
GNU tar 1.35
dpkg 1.22.22
GNU patch 2.8
git 2.47.3
Linux 6.12.13 x86_64 GNU/Linux
```

Hosted exact gate target:

```text
GitHub ubuntu-24.04 runner
canonical mmdebstrap main 77ec9be5417ee44c96343d2347145585da1b1f94
```

## Exact source identities

- `tarfilter` blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- `coverage.txt` blob: `87f4cccf5fc646c82600672113830419e20b95dd`
- `coverage.py` blob: `9a522484aef05deae514a98e4b6adf5feb6c886d`
- `run_null.sh` blob: `e0a8c106f9d3d636baea286d2ab33834748dffc9`
- patch blob: `fca86c0a45cb7f7c2e8534b4dacf8b2dafd55342`
- locally computed patch SHA-256: `e9a71c6afe34f3170c27cc81a93006bf5d6eb2fe863fd7dd32e7f46c8719171b`
- test blob: `516f4e1f3a38175257b68a9d9e524495d7531564`
- locally computed test SHA-256: `9fbc4c1146bdeb199713eb51279ce439e78ff96fc7be711f68b2278aa052e910`

The exact workflow recomputes and uploads hashes; its artifact is required before disposition changes.

## Original narrow baseline receipt

Command retained in `artifacts/baseline-native-test.txt`:

```sh
MMTARFILTER=/tmp/tarfilter-baseline /tmp/tarfilter-path-dotfiles
```

Result: exit `1`.

First failure:

```text
AssertionError: {'..name', '../config', '...name', '/./.config', '././config', './.config', './config', 'config', '/config', '.config', '././.config'}
```

Interpretation: current source retained every dotfile spelling under `--path-exclude=/.config` and aliased ordinary and parent-component names.

This receipt belongs to the earlier test revision. The final exact workflow reruns the expanded current test against the same exact source blob and requires a nonzero baseline result.

## Mutation and losing-candidate matrix

Command:

```sh
python3 scripts/test_normalization_mutations.py
```

Durable receipt: `artifacts/normalization-mutations.json`.

Required losing mutations:

| Mutation | Distinguishing loss |
| --- | --- |
| current `lstrip("./")` | `.config` and `../config` alias ordinary names |
| remove one optional prefix | `././.config` remains partly prefixed |
| `posixpath.normpath()` | `../config` and internal `foo/./.config` collapse |
| first loop candidate | `.` and `./.` map to `/.` instead of `/` |

Selected helper result: every retained mapping assertion passes.

## Real dpkg differential

Command:

```sh
sudo python3 scripts/probe_dpkg_path_filters.py
```

Durable receipt: `artifacts/dpkg-path-filter-differential.json`.

The script creates disposable `.deb` archives, isolated roots, and isolated dpkg admin directories.

Results on dpkg 1.22.22:

| Member | Filter | Payload result |
| --- | --- | --- |
| `./.config` | `/.config` | excluded |
| `./.config` | `/config` | retained as `.config` |
| `./config` | `/config` | excluded |
| `./config` | `/.config` | retained as `config` |
| `./..name` | `/..name` | excluded |
| `./...name` | `/...name` | excluded |
| `.config` | `/.config` | retained |
| `././.config` | `/.config` | retained |

Interpretation: native dpkg path filtering supports the ordinary package-member form `./path`. Repeated and bare leading spellings are a separate consumer compatibility extension.

## GNU tar consumer path matrix

Command:

```sh
python3 scripts/probe_tar_path_aliases.py
```

Durable receipt: `artifacts/gnu-tar-path-aliases.json`.

Results on GNU tar 1.35:

- `.config`, `./.config`, `././.config`, `/./.config`, `//./.config`, `.//.config`, and `/.//.config` extract as `.config`.
- `.`, `./`, `./.`, `/.`, `/./`, and `//./.` address extraction root and apply the stored directory mode there.
- `foo/./.config` and `foo/.config` extract to the same internal pathname.
- `..`, `../config`, and `./../config` are rejected.

The first two groups support the selected leading-prefix and root behavior. The internal-dot group is retained as a successor question.

## Current upstream-style regression

Path:

```text
tests/tarfilter-path-dotfiles
```

Executable authority:

1. explicit `MMTARFILTER`;
2. checkout-local `./tarfilter`;
3. system `/usr/bin/mmtarfilter` fallback.

The test covers:

- both dotfile/plain exclusion directions;
- include-after-exclude and reversed option order;
- multi-dot names and parent components;
- repeated and alternating leading prefixes;
- archive-root aliases;
- regular, directory, symlink, and hard-link types;
- retained payload bytes;
- mode, uid/gid, timestamp, PAX-header, and link-target preservation.

## Patch transport gate

The exact workflow performs these commands on two fresh canonical clones:

```sh
patch --dry-run --fuzz=0 -p1 -d "$work" -i "$patch_file"
git -C "$work" apply --check --verbose "$patch_file"
git -C "$work" apply --verbose "$patch_file"
test -x "$work/tests/tarfilter-path-dotfiles"
```

Reason for both tools:

- GNU `patch` supplies an explicit no-fuzz/no-offset text check.
- Git application owns the declared executable mode for the new test.

The workflow then requires exactly these changed files:

```text
coverage.txt
tarfilter
tests/tarfilter-path-dotfiles
```

It also runs `git diff --check` and retains the full binary-capable diff.

## Syntax and style gates

Per fresh candidate generation:

```sh
python3 -m py_compile tarfilter
sh -n tests/tarfilter-path-dotfiles
shellcheck --exclude=SC2050,SC2194,SC2016 tests/tarfilter-path-dotfiles
shfmt --posix --binary-next-line --case-indent --indent 2 --simplify -d \
  tests/tarfilter-path-dotfiles
```

## Direct candidate gate

Per fresh candidate generation:

```sh
MMTARFILTER="$work/tarfilter" "$work/tests/tarfilter-path-dotfiles"
```

Expected result: exit `0`, empty stdout and stderr.

## Registered upstream runner gate

Per fresh candidate generation:

```sh
mkdir -p shared/cache/debian/dists/unstable
: >shared/cache/debian/dists/unstable/InRelease
HAVE_QEMU=no SOURCE_DATE_EPOCH=0 CMD=./mmdebstrap \
  ./coverage.py --exitfirst tarfilter-path-dotfiles
```

`SOURCE_DATE_EPOCH=0` keeps the focused null-backend test independent of mirror timestamp parsing. `coverage.py` copies `tarfilter` and the registered test into `shared`, and `run_null.sh` executes the checkout-local copy.

## Cleanup and immediate rerun

After each registered run, the workflow records source status, removes `shared` and all `__pycache__` directories, and requires the remaining source changes to equal the intended three-file candidate.

The complete direct and registered sequence then runs from a second fresh canonical clone named `immediate-rerun`.

## Internal exact-execution carrier

- Draft PR: #408
- Last semantic technical head before documentation batch: `7b92189ace1de4138d753830f8032c244f1276c6`
- Workflow run for that head: `30691603829`
- Last observed status: queued
- Earlier queued generations motivated branch-scoped concurrency and cancellation for future superseded heads.

The final documentation commit generates a replacement exact-head run. That run, its jobs, logs, artifacts, and exact hashes become authoritative.

## Complete diff review

The upstream candidate changes only:

- `tarfilter` — helper plus one call-site replacement;
- `coverage.txt` — one test registration;
- `tests/tarfilter-path-dotfiles` — focused regression.

It contains no parent-retention, sparse, no-option, transform, PAX-filter, strip, type-filter, ID-shift, or link-target rewrite implementation.

The Linux Fieldwork branch additionally carries packet documentation, scripts, receipts, and the guarded workflow. Those files are internal evidence, not upstream diff content.

## Tests still unexecuted on the final documentation head

- completed exact-head workflow and artifact inspection;
- full `coverage.sh` suite;
- Debian package/autopkgtest execution;
- cross-version Python matrix;
- controlled Forgejo fork branch and compare view;
- maintainer compatibility review for the repeated-prefix extension.

The focused exact-head workflow is the first incomplete gate. Broader package and full-suite runs follow only if the focused result or review reveals a reason to expand.
