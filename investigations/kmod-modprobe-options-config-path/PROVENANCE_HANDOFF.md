# Provenance-aware recursive option handoff

## State

- Investigation: recursive `modprobe` configuration identity and adjacent empty-environment allocation correctness
- Disposition: `HOLD — recursive defect proven on current master; fallback carrier blocked; allocator repair independently validated`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork technical head before this handoff update: `89f26be1c6a3ad1fed6f17cb88dd4fe2f790fa1c`
- Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#412`
- Native characterization: `teamleaderleo/kmod#1@84ba8ae9db4f455965efa22afdd5cb177781106b`
- Provenance fallback experiment: `teamleaderleo/kmod#5@94c42b0374c5b668eaf8f31a8daf79da1b268be0`
- Empty-environment allocation repair: `teamleaderleo/kmod#6@9dbb2701a2fcf96280a99b8d2ebcb4b0451be6b3`
- Formal reviews: none
- External contact: unauthorized; none made

## Source freshness

The original exact execution base was:

```text
kmod master: 5086df53090b2fe9fa1c31351c05a78a12a4ba71
modprobe.c:  413960cae0f39945a3f2d6509dc4a8c262ae2609
```

Exact upstream master used for the final refresh is:

```text
kmod master: dae6c02ffed2e8d16da8dba16d974fc955eebb1f
modprobe.c:  c4b5021137a01529d75d9979e262308ce371bbae
```

Source review and exact execution both show the relevant mechanisms remain present on that August 6, 2026 head:

- `env_modprobe_options_append()` still flattens option values into the single `MODPROBE_OPTIONS` string;
- `prepend_options_from_env()` still uses the old pointer-array allocation expression, copies `envlen + 1`, and uses the same space/quote parser.

Final exact-current refresh:

```text
workflow: .github/workflows/kmod-current-master-refresh.yml
run:      31143700852
GCC job:  92758721115
Clang job:92758721114
```

Both jobs passed exact source identity, ASan/UBSan build, two runs of the recursive configuration discriminator, the required explicit-empty ASan failure, cleanup, and artifact upload.

Artifacts:

```text
GCC:   8980706391  sha256:196244ac10e4ff7e2274b2e9ebd2a8a4d60eb841070ec2b6dc4eb6b2b52a32d8
Clang: 8980707642  sha256:0865ccc0ba4e5b32d26a91a34d839191b3409b55af038006bbf22d361e504d39
```

## Closed recursive-configuration baseline

Final native characterization run `30850597196` completed successfully under GCC and Clang sanitizers.

Both compiler jobs observed exactly:

```text
FAILED: modprobe_options_config_path_space
PASSED: modprobe_options_config_path_control
```

Package-style and exact-source behavior remains:

```text
no-space configuration path: parent/nested marker counts 1/1
spaced configuration path:   parent/nested marker counts 1/0
parent status: 0
nested status: 0
```

The current-master refresh reproduced that discriminator twice under both compilers. The parent uses the requested configuration. An `install` command starts another `modprobe`; the parent serializes `-C` and its raw pathname into `MODPROBE_OPTIONS`; the child reparses a changed argument vector and can silently use another configuration.

No unrelated failure, dirty fake-root state, loaded-module residue, or sanitizer finding occurred in the recursive characterization.

## Transport design review

### V1 — legacy parser rewrite held

PR #2 changes raw-backslash behavior and does not bound recursive option growth. It remains execution history, not selected source.

### Narrow exact-record V2 held

PR #3 carries only generated `-C/-s/-q/-v` state. A reversing inherited-`-d` control proved current kmod can preserve additional private options that this design drops.

### Strict provenance rejected

PR #4 separates inherited state from exact generated state, but rejects an install script that mutates `MODPROBE_OPTIONS` by appending `-q`. Current kmod accepts that mutation for representable legacy values, so strict mismatch rejection is not recursively equivalent.

### Provenance fallback experiment blocked on carrier reconstruction

PR #5 tests a bounded fallback after exact metadata validates:

1. compare the actual legacy mirror with the expected inherited-plus-generated mirror;
2. when an install script changed the mirror, rebase the actual string as inherited state;
3. clear the exact generated suffix;
4. parse the rebased inherited state with the unchanged legacy parser;
5. publish it once to avoid later duplication;
6. continue to reject malformed exact/base records and positional exact records.

Local GCC 14.2 and Clang 17 ASan/UBSan multicall builds passed spaced recursive `-C` through three dependency-free levels, inherited `-d`, install-script `-q` mutation, repeated and clustered options, representable mixed-version direction, and safe malformed-state boundaries.

Hosted recovery run:

```text
head:  94c42b0374c5b668eaf8f31a8daf79da1b268be0
run:   31047684477
GCC:   92447161754
Clang: 92447161730
```

The committed Base64 carrier matched its pinned digest. Decompression produced output despite the known gzip CRC/length damage, but both jobs then failed before source execution at:

```text
error: corrupt patch at .../fallback.patch:889
```

`git apply --check` never succeeded; formatting, build, native tests, and the fallback discriminator were skipped. Cleanup and failure receipts completed successfully.

The recovered patch is therefore syntactically corrupt in addition to the damaged gzip trailer. Do not treat run `31047684477` as source evidence. Reconstruct a clean patch from trustworthy retained source/history before any further hosted fallback execution.

The fallback remains an experiment. It cannot recover pathname identity after an old parent has already flattened an unrepresentable value.

## Separate empty `MODPROBE_OPTIONS` allocation defect

When `MODPROBE_OPTIONS` exists but is empty, exact `prepend_options_from_env()` calculates no independent string storage and then copies the terminating NUL. The old base and exact August 6 current master reproduce under both GCC and Clang ASan:

```text
AddressSanitizer: heap-buffer-overflow
WRITE of size 1
```

The ordinary non-sanitized Debian binary still exits successfully. No exploitability or security-severity claim is made.

### Final allocator candidate

PR #6 keeps product source uncommitted and carries one exact two-file patch plus a read-only validator. The candidate:

- calculates pointer count and pointer bytes independently;
- calculates `envlen + 1` string bytes independently;
- uses checked multiplication/addition;
- leaves the legacy parser and raw-backslash behavior unchanged;
- adds a native `MODPROBE_OPTIONS=""` test using `modprobe --version`.

Exact carrier identity:

```text
head:         9dbb2701a2fcf96280a99b8d2ebcb4b0451be6b3
patch blob:   08612258b78b1b0529bf2bc999ac88d1df21cb94
patch sha256: eb043a8ba8579353723da0c68987cbccf86cb4b492278e4791016602f727a07d
file fence:   testsuite/test-modprobe.c tools/modprobe.c
```

Final old-base gate:

```text
run:   31143505815
GCC:   92758131800
Clang: 92758131757
```

Both jobs first reproduced the exact unmodified ASan loss, then passed patch application, exact two-file fence, clang-format, sanitizer build, direct explicit-empty success, focused `test-modprobe`, complete native suite, cleanup, and receipt upload.

Artifacts:

```text
GCC:   8980651971  sha256:515b97bffeb84e8d300791ea363691b07497eed3aea592b179317663fb1eeb16
Clang: 8980648324  sha256:f0d247ffaed4233332f8e41b0feaa1ff29dbdcabd76828b2a8ee5d1063d69f63
```

### Exact current-master candidate gate

The same final carrier applies directly to exact August 6 upstream master `dae6c02ffed2e8d16da8dba16d974fc955eebb1f` and passes:

```text
workflow: .github/workflows/kmod-current-master-empty-candidate.yml
run:      31143700889
GCC job:  92758721094
Clang job:92758721113
```

Both jobs passed exact source/carrier identity, patch application and two-file fence, formatting, sanitizer build, direct explicit-empty execution, focused `test-modprobe`, complete native suite, recursive scope control, cleanup, and receipt upload.

Artifacts:

```text
GCC:   8980711844  sha256:927aa6e2889e1a0c0126446998c9d1438f9f50761e753dc23901eab679068a51
Clang: 8980710940  sha256:387384f4671c049b5bed2c58930d13949d922774f61325a5947cb6b8fe1b4d65
```

The recursive scope control still shows the independent no-space `1/1` versus spaced-path `1/0` split.

One earlier current-master Clang generation failed after a successful build because the workflow left `CC` unset during Meson tests. `scripts/sanitizer-env.sh` assumed GCC and preloaded GCC ASan into a Clang-ASan binary. A workflow-only correction exported the matrix compiler; the pinned upstream source and allocator patch stayed unchanged, and the corrected run above is green.

### Standard final-head CI

At PR #6 head `9dbb2701a2fcf96280a99b8d2ebcb4b0451be6b3`, all observed standard fork CI is green:

- clang-format: `31143505841`;
- Build and Test: `31143505824`;
- Code Coverage: `31143505830`;
- CodeQL: `31143505832`;
- codespell: `31143505820`;
- dedicated allocator validation: `31143505815`.

The allocator repair is independently validated on the original exact base and exact current upstream head. It does not require choosing a recursive transport policy.

## Overlap refresh

The last open upstream issue/PR searches found no matching implementation for:

- recursive `MODPROBE_OPTIONS` configuration-path identity with whitespace;
- explicitly empty `MODPROBE_OPTIONS` heap-buffer-overflow;
- `prepend_options_from_env()` allocation correction.

Searches can miss differently worded work. Refresh immediately before any authorized public action.

## Stop rule

Do not select or publish a recursive transport repair until:

1. the fallback source is reconstructed from a trustworthy clean artifact or history;
2. the reconstructed fallback passes exact file fencing, formatting, GCC/Clang sanitizer builds, focused reruns, complete suite, and safe discriminator;
3. mixed-version and install-script mutation limitations remain documented honestly;
4. no temporary carrier remains in a selected source diff;
5. standard final-head CI is inspected;
6. overlap, contribution policy, and formal review state are refreshed.

The allocator lane has cleared its technical gates. Product source remains uncommitted, so any next allocator step should be a clean source-only owned-fork candidate or an explicitly retained patch-only handoff. Upstream publication still requires separate authorization.

## First incomplete steps

1. Reconstruct PR #5's fallback patch from trustworthy retained source/history; do not reuse the corrupt recovered patch at line 889.
2. If continuing the recursive lane, rerun the full fallback matrix only after a clean reproducible carrier exists.
3. For the allocator lane, consider a clean source-only owned-fork candidate based on the validated two-file patch.
4. Refresh overlap and formal-review state immediately before any promotion decision.
5. Do not contact upstream without explicit authorization.
