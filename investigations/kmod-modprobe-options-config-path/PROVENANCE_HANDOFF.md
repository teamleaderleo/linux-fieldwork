# Provenance-aware recursive option handoff

## State

- Investigation: recursive `modprobe` configuration identity
- Disposition: `HOLD — baseline complete; v1/v2 blocked; strict provenance rejected; fallback and empty-env repair executing`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork head before this update: `0265af65b377a0a48b2b3e05054df076e9098dda`
- Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#412`
- Exact public/fork kmod base: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Base `tools/modprobe.c` blob: `413960cae0f39945a3f2d6509dc4a8c262ae2609`
- Native characterization: `teamleaderleo/kmod#1@84ba8ae9db4f455965efa22afdd5cb177781106b`
- Candidate v1: `teamleaderleo/kmod#2@8ce150bbff70d0801347170741703ed22ed7ea1f` — held
- Narrow exact-record v2: `teamleaderleo/kmod#3@c9b83dc0fa8aa7376560204e9bb5640b43323751` — held
- Strict provenance: `teamleaderleo/kmod#4@bac99e066b029373599dc20df4c8feb470e4e2f6` — rejected by reversing control
- Provenance fallback: `teamleaderleo/kmod#5@8c961c96e3092435fdbab232a907b477c10f74dd` — executing
- Empty-environment allocation repair: `teamleaderleo/kmod#6@02c84e20299f134dfffba99c9dee4efca5311bb2` — executing
- Formal reviews: none
- External contact: unauthorized; none made

## Closed baseline evidence

Exact current source and the target-native losing regression are complete under GCC and Clang sanitizers.

```text
no-space config path: parent/nested 1/1
spaced config path:   parent/nested 1/0
parent and nested statuses: 0
```

Final native characterization in Linux Fieldwork run `30850597196` showed exactly one intentional failure and one passing control under each compiler:

```text
FAILED: modprobe_options_config_path_space
PASSED: modprobe_options_config_path_control
```

No unrelated failure, dirty fake-root state, loaded-module residue, or sanitizer finding occurred.

## Candidate progression

### V1 — parser rewrite held

V1 changes existing raw-backslash parsing and does not bound inherited-option duplication. Its carrier finally parses and materializes correctly, but a green run cannot select it.

Current read-only validation:

```text
head: 8ce150bbff70d0801347170741703ed22ed7ea1f
run: 30956120441
job: 92149449308
latest observation: queued
```

### Narrow V2 — generated subset held

V2 preserves the legacy parser and carries a length-delimited exact record, but rebuilds only `-C/-s/-q/-v`.

A reversing inherited-`-d` control proved current kmod preserves additional private options across recursion while v2 drops them. The design is therefore not recursively equivalent.

Its carrier was repaired to pin seven source fragments separately instead of trusting a stale aggregate hash.

```text
head: c9b83dc0fa8aa7376560204e9bb5640b43323751
run: 30957132015
GCC job: 92152714899
Clang job: 92152714803
latest observation: queued
```

### Strict provenance — mechanism useful, policy rejected

Strict provenance separates:

1. an inherited private-string base;
2. an exact generated suffix;
3. a base-length field identifying the inherited prefix in the compatibility mirror.

It preserves inherited `-d`, attached and clustered options, repeated `-C`, spaced recursive identity, and stable three-level state under local GCC/Clang ASan/UBSan builds.

A reversing control then showed that current kmod permits an install script to mutate `MODPROBE_OPTIONS` by appending `-q`. Strict provenance treats the changed mirror as corruption and fails. That is a compatibility-policy regression, so PR #4 is retained as history but is not selected.

### Provenance fallback — current transport experiment

PR #5 tests a bounded fallback only after exact/base metadata has decoded successfully:

- compare actual `MODPROBE_OPTIONS` with the expected base-plus-generated mirror;
- when an install script changed the mirror, rebase the actual legacy string as the inherited base;
- clear the generated exact suffix;
- parse the rebased base with the unchanged legacy parser;
- continue to reject malformed exact records, malformed base metadata, and positional exact records;
- publish the rebased base once so later recursion does not duplicate it.

The mutation fixture deliberately uses a path without whitespace. This separates install-script mutation compatibility from the existing legacy grammar defect for quoted spaced paths followed by appended options.

Local complete multicall GCC 14.2 and Clang 17 ASan/UBSan builds passed:

- spaced recursive `-C` through three dependency-free levels;
- inherited base plus exact generated suffix;
- inherited `-d` nested lookup;
- install-script mutation by appending `-q`;
- attached short/long `-C`, options after a non-option, clustered `-qv`, and repeated `-C` order;
- stable three-level inherited/exact/mirror state;
- representable new-parent/old-child recursion;
- visible failure for unrepresentable new-parent/old-child values;
- expected unrecoverable old-parent/new-child direction.

Exact local fallback binary hashes:

```text
GCC:   c80dfb4b86236869e4ebb77d8053c746d7d11c92fbbb31ebd5722a26aee831bc
Clang: eb6b00a5599d3244558bc0b2301d73396453d78763493aa24a44ad5d89d6d800
```

The first hosted fallback run failed before source execution because the workflow pinned stale decoded-gzip and reconstructed-patch hashes. The committed base64 carrier was stable. The workflow now pins that committed carrier and records derived hashes after decoding.

```text
head: 8c961c96e3092435fdbab232a907b477c10f74dd
run: 30957536612
GCC job: 92153958486
Clang job: 92153958380
latest observation: queued
```

This remains an experiment. A green run establishes mechanics, not maintainer policy or mixed-version equivalence.

## Separate empty `MODPROBE_OPTIONS` allocation defect

Exact current `prepend_options_from_env()` allocates:

```c
sizeof(char *) * (argc + space_count + 3 + envlen)
```

and places the copied string after `argc + space_count + 3` pointers. When `envlen == 0`, no byte remains for the terminating NUL, but `memcpy(str, env, envlen + 1)` writes one byte.

A standalone transcription of the exact function produced:

```text
AddressSanitizer: heap-buffer-overflow
WRITE of size 1
```

under GCC 14.2 and Clang 17. The ordinary Debian `kmod 34.2` binary still exited successfully, so this is a source-level memory-correctness finding, not a demonstrated crash, exploit, or security-severity result.

No matching open upstream issue or pull request was found.

PR #6 isolates a minimal behavior-preserving repair:

- calculate pointer storage and string storage independently;
- use checked addition and multiplication;
- allocate `envlen + 1` bytes for the copied string;
- retain the current parser and raw-backslash behavior unchanged;
- add a native `MODPROBE_OPTIONS=""` test using `modprobe --version`, without module syscalls.

Local GCC/Clang ASan/UBSan controls passed for empty input, raw-backslash input, and ordinary `-q -v` input.

```text
patch SHA-256: 0a36ad1a5c72fa44aa2fa7acd642586a36e2df8a0f30c01b947400631a15ad15
head: 02c84e20299f134dfffba99c9dee4efca5311bb2
run: 30957800012
GCC job: 92154784159
Clang job: 92154784197
latest observation: queued
```

The hosted gate requires the exact unmodified baseline to lose under ASan before the candidate is applied, then requires the direct control, formatting, focused native test, complete suite, cleanup, and retained receipts.

## Kernel source-tree boundary

The Linux kernel source repository contains the kernel itself: architecture code, drivers, memory management, filesystems, networking, scheduler and other core kernel code, security hooks, the block layer, IPC, sound, virtualization, headers, build tooling, documentation, and in-tree tests/tools.

`kmod` is not part of that tree. It is a separate userspace project that provides `modprobe`, `depmod`, `insmod`, `rmmod`, `lsmod`, and `libkmod`. Other adjacent projects such as systemd, glibc, iproute2, util-linux, bash, coreutils, and package managers are also separate userspace projects.

## Current stop rule

Do not select or publish a recursive transport repair until:

1. the fallback workflow is terminal under GCC and Clang;
2. focused reruns and the complete suite pass without sanitizer findings;
3. exact carrier and materialized source/test identities are retained;
4. install-script mutation behavior is compared with exact current source;
5. mixed-version limitations are stated explicitly;
6. temporary carriers are absent from one exact final source diff;
7. standard final-head CI is inspected;
8. overlap, contribution policy, and review state are refreshed immediately before any authorized publication decision.

Treat the empty-environment allocation repair separately. It can be reviewed on its own two-file fence and does not require resolution of the recursive transport policy.

## First incomplete steps

1. Inspect fallback run `30957536612`.
2. Inspect empty-environment run `30957800012`.
3. Inspect the held v1/v2 runs only as execution evidence, not source-selection gates.
4. If the empty-environment repair passes, retain its exact baseline/candidate artifacts and assess it independently.
5. If the fallback passes, compare hosted receipts with the local GCC/Clang evidence before considering any final source branch.

No public kmod-project interaction is authorized or performed.
