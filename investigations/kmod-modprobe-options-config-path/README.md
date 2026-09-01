# kmod nested modprobe loses a spaced configuration path

## TL;DR

A parent `modprobe -C "/path with spaces" module` reads the requested configuration correctly. When an `install` rule launches another `modprobe`, kmod exports the parent option as an unquoted string such as `MODPROBE_OPTIONS=-C /path with spaces`. The nested parser splits that into different arguments, silently uses the default configuration, and exits `0`.

The behavior reproduces with Debian `kmod 34.2-2` as both root and the unprivileged `nobody` user. Current upstream master `5086df53090b2fe9fa1c31351c05a78a12a4ba71` still contains the same raw append and hand-written parser. The next step is to run the retained test against an exact master build and compare robust serialization or non-string propagation candidates.

## Explain like I'm five

`modprobe` can be told, “use the rules in this special folder.” Some rules call `modprobe` again.

Literal example:

```text
parent gets:  -C "/tmp/config folder"
parent uses:  /tmp/config folder       -> correct
parent passes: MODPROBE_OPTIONS=-C /tmp/config folder
child reads:  -C /tmp/config  + extra word "folder"
child uses:   default rules            -> wrong, but status 0
```

The first command remembers the folder as one pathname. The nested command receives a flattened string and loses that identity.

## Why care

The affected boundary controls aliases, blacklists, module options, install/remove commands, soft dependencies, weak dependencies, and configuration ordering. A caller can observe the parent honoring one policy while an install/remove rule's nested `modprobe` silently uses another policy.

This investigation does not claim that arbitrary third-party `MODPROBE_OPTIONS` strings are a stable interface. It focuses on kmod's own documented `-C` propagation through install/remove rules.

## Current state

- State: `EXECUTING`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Exact evidence head before this investigation record: `ac7d04833fc1451512ea794f662e011ed0dd6e21`
- Latest authoritative gate: deterministic local matrix passed twice; the same distinguishing result passed as EUID `0` and EUID `65534`
- First incomplete step: build exact upstream master `5086df53090b2fe9fa1c31351c05a78a12a4ba71`, run the retained regression unchanged, then add a source-level mutation/candidate matrix
- Cleanup state: complete; temporary config directories, helper scripts, and receipts were deleted by `TemporaryDirectory`
- Next safe action: add the test to a current upstream checkout and compare candidate argument-serialization mechanisms without invoking real module syscalls
- External-contact state: unauthorized; no kmod issue, email, pull request, comment, or review created

## Intent and precedent

Current `modprobe(8)` says:

- `-C` is passed through install or remove commands to other `modprobe` commands in `MODPROBE_OPTIONS`;
- `MODPROBE_OPTIONS` originates with the implementation of install rules;
- the environment format is intentionally undocumented because third-party use is discouraged.

Commit `42d60a3267162a36ec6b6b39a7b91e5078b90979` added that explanation and explicitly noted that the environment can alter configuration directories.

Current master `tools/modprobe.c`:

1. appends `"-C"` to `MODPROBE_OPTIONS`;
2. appends `optarg` as raw text;
3. prepends the environment to the next command line with a custom parser that counts and splits literal spaces and removes matching single or double quotes.

Interpretation: third-party syntax is deliberately private, but exact internal propagation of a valid `-C` pathname is intended. The raw string append does not preserve that pathname when it contains whitespace.

## Question

When a parent `modprobe` uses an `install` rule, does the nested `modprobe` receive and use the exact same `-C` configuration directory, including a directory name containing a space?

## Source

- Project: kmod
- Canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`
- Source-reading mirror: `https://github.com/kmod-project/kmod.git`
- Requested revision: current `master`
- Resolved mirror commit observed 2026-08-01: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Source owner: `tools/modprobe.c`
- Relevant functions: `env_modprobe_options_append()`, `prepend_options_from_env()`, and option case `'C'`
- Intent commit: `42d60a3267162a36ec6b6b39a7b91e5078b90979`
- Candidate source commit: none yet
- Local source checkout: unavailable in the first runtime because DNS resolution failed
- Local executable: Debian `/usr/sbin/modprobe`, package `kmod 34.2-2`

## Environment

```text
Distribution package: kmod 34.2-2 amd64
libkmod package: libkmod2 34.2-2 amd64
modprobe: /usr/sbin/modprobe
modprobe SHA-256: a775c12b9d71d9548654ff98ecc0e5e3378bdaccd52ccb62fa80a5f41e849caf
modprobe version: 34.2 (+ZSTD +XZ -ZLIB +OPENSSL)
Kernel: Linux 6.12.13 x86_64 GNU/Linux
Shell used by install rule: /bin/sh
Privilege controls: EUID 0 and EUID 65534
Context: disposable container/runtime; no module insertion or removal
```

## Baseline behavior

The test creates a configuration directory containing:

```text
blacklist lf_space_marker
install lf_outer_space /tmp/.../helper.sh
```

The helper records `MODPROBE_OPTIONS` and runs `modprobe -c`.

Observed spaced-path case:

```text
parent direct config dump marker count: 1
parent install-rule invocation status: 0
MODPROBE_OPTIONS: -C $TMP/space/conf dir
nested config dump status: 0
nested marker count: 0
nested stderr: empty
```

The no-space control retains the marker in both parent and nested config dumps.

## Hypothesis or candidate

The mismatch is caused by string serialization rather than configuration loading itself:

- direct argv preserves a spaced pathname;
- manually quoting the same pathname inside `MODPROBE_OPTIONS` preserves it;
- kmod's internal append does not quote it;
- the nested parser therefore changes one argument into multiple arguments.

A candidate must preserve the exact internal argv across recursion. It must also define behavior for quote characters, tabs, repeated whitespace, empty arguments, pre-existing `MODPROBE_OPTIONS`, multiple `-C` values, and malformed externally supplied strings.

No implementation is selected yet. Possible mechanisms include a well-defined internal encoder/decoder pair or avoiding generic string serialization for internally propagated configuration paths. A partial “wrap in quotes” repair is not sufficient until quote-containing pathnames and composition with existing values are tested.

## Reproduction

Run:

```sh
python3 investigations/kmod-modprobe-options-config-path/test_modprobe_options_config_path.py \
  > investigations/kmod-modprobe-options-config-path/artifacts/result.json
```

The script:

1. creates no-space and spaced configuration directories;
2. verifies each direct `modprobe -C DIR -c` sees its marker;
3. invokes a synthetic module name with an `install` helper;
4. records the helper's `MODPROBE_OPTIONS`;
5. runs nested `modprobe -c` and counts the marker;
6. checks a manually quoted environment control;
7. checks repeated-space, tab, and unmatched-quote parser controls;
8. normalizes temporary paths to `$TMP` for deterministic output;
9. deletes all temporary state on exit.

Unprivileged control:

```sh
runuser -u nobody -- \
  python3 investigations/kmod-modprobe-options-config-path/test_modprobe_options_config_path.py
```

## Results

### Main matrix

| Case | Direct marker | Parent status | Nested status | Nested marker |
|---|---:|---:|---:|---:|
| config path without spaces | 1 | 0 | 0 | 1 |
| config path with a space | 1 | 0 | 0 | 0 |

### Parser controls

| `MODPROBE_OPTIONS` form | Status | Marker |
|---|---:|---:|
| normal single-quoted spaced path | 0 | 1 |
| leading and repeated spaces | 0 | 0 |
| tab separator | 0 | 0 |
| unmatched quote | 0 | 0 |

### Exact retained identities

```text
test script SHA-256: 8006c8cb24ef44803565fb580bd9334edb807e210f3a5c0f313679f260c211c1
root result SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
immediate normalized rerun SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
unprivileged result SHA-256: 759550141d24d03543d0686b235e82b0aab8015181b50bddb169e9d297acd9cf
```

The normalized root run and immediate rerun are byte-identical. The unprivileged run has the same distinguishing fields.

## Interpretation

### Demonstrated

- A valid `-C` directory containing spaces is accepted and used by the parent.
- kmod's own install-rule propagation exports the path without quoting.
- The nested parser changes the path's argv identity.
- The nested command silently uses different configuration and exits successfully.
- The behavior does not depend on root privileges or real kernel-module operations.
- Manually quoted environment input is a passing control, so the failure is not caused by `kmod_new()` rejecting spaced paths.

### Plausible consequence

Nested install/remove rules may observe different aliases, blacklists, options, command overrides, or dependency policy than the parent invocation when the chosen config path contains whitespace.

### Open design question

The environment format is deliberately private. The fix should therefore preserve kmod's internal contract without accidentally promising shell syntax or broadening unsupported third-party behavior. The safest representation and compatibility boundary remain to be tested.

## Cross-context review

- **Direct versus recursive call path:** direct `-C` passes; recursive install-rule propagation loses.
- **Identity:** one pathname becomes two argv elements.
- **Evidence path:** both commands exit `0`, so status-only testing would miss the policy change.
- **Privilege:** root and unprivileged controls agree.
- **Parser behavior:** properly quoted input passes; repeated spaces, tabs, and unmatched quotes silently change behavior.
- **Cleanup:** no modules, processes, mounts, sockets, or temporary paths remain after the test.

## Evidence boundary

- Runtime behavior is demonstrated on Debian `kmod 34.2-2`, not an executed build of current master.
- Current master applicability is source-reviewed because the same append/parser mechanism remains at commit `5086df53090b2fe9fa1c31351c05a78a12a4ba71`.
- No real module was inserted, removed, or resolved. The `install` rule intentionally replaces module insertion with a helper.
- Only a space-containing path is used for the internal recursion discriminator. Quote characters, tabs, newlines, and other unusual pathname bytes remain candidate tests.
- Multiple simultaneous `-C` values and pre-existing valid environment values remain untested.
- No security severity is assigned. This is currently a wrong-policy/silent-success finding.
- Upstream testsuite execution, sanitizers, GCC/Clang builds, and other libc implementations remain unexecuted.

## Next step

1. Obtain an exact checkout of master `5086df53090b2fe9fa1c31351c05a78a12a4ba71`.
2. Add the retained regression to `testsuite/test-modprobe.c` using the fake rootfs/exec harness.
3. Prove current master loses under that native test.
4. Compare candidate propagation mechanisms with spaced, quoted, repeated-whitespace, pre-existing-environment, and multiple-`-C` controls.
5. Run the focused test under default sanitizer-enabled development flags with GCC and Clang.
6. Recheck active upstream issues and pull requests immediately before any publication decision.

## Stop rule

This investigation may move from `EXECUTING` to `REVIEW` when one exact current-master head has:

- a losing native baseline;
- a passing candidate with complete argument-identity controls;
- direct and recursive path parity;
- rootless/fake-syscall execution;
- sanitizer-enabled GCC and Clang focused runs;
- clean rerun and no retained state;
- complete diff and documentation review;
- active overlap recheck;
- explicit residual risks and reopen triggers.

## Authority

No external interaction is authorized or performed. This branch, target map, test, and evidence are internal Linux Fieldwork records only.
