# Provenance-aware recursive option handoff

## State

- Investigation: recursive `modprobe` configuration identity and adjacent empty-environment allocation correctness
- Disposition: `HOLD — proven baseline; exact current-master refresh and two independent repair lanes executing`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork technical head before this handoff update: `156b398c64652c36273e65f4df5fd2c287e9ede3`
- Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#412`
- Native characterization: `teamleaderleo/kmod#1@84ba8ae9db4f455965efa22afdd5cb177781106b`
- Provenance fallback experiment: `teamleaderleo/kmod#5@94c42b0374c5b668eaf8f31a8daf79da1b268be0`
- Empty-environment allocation repair: `teamleaderleo/kmod#6@b55841035fc32a2231057edf94966b5786aca22e`
- Formal reviews: none
- External contact: unauthorized; none made

## Source freshness

The original exact execution base was:

```text
kmod master: 5086df53090b2fe9fa1c31351c05a78a12a4ba71
modprobe.c:  413960cae0f39945a3f2d6509dc4a8c262ae2609
```

Upstream master advanced on 2026-08-05 to:

```text
kmod master: f9fa9becf86956b9a84413a5bfa2e83dcff8370d
modprobe.c:  c4b5021137a01529d75d9979e262308ce371bbae
```

It is six commits ahead. The new commits reorganize getopt handling and adjacent tooling, but source review shows the relevant mechanisms remain unchanged:

- `env_modprobe_options_append()` still flattens option values into the single `MODPROBE_OPTIONS` string;
- `prepend_options_from_env()` still allocates with the old pointer-array expression, copies `envlen + 1`, and uses the same space/quote parser.

A dedicated exact-current workflow now verifies the new head and blob before execution:

```text
workflow: .github/workflows/kmod-current-master-refresh.yml
run:      31047887468
GCC job:  92447816286
Clang job:92447816227
latest observation: queued
```

Each job builds exact current master under ASan/UBSan, runs the recursive configuration discriminator twice, and independently requires the explicitly empty `MODPROBE_OPTIONS` path to reproduce the one-byte ASan write.

## Closed recursive-configuration baseline

Final native characterization run `30850597196` completed successfully under GCC and Clang sanitizers.

Both compiler jobs observed exactly:

```text
FAILED: modprobe_options_config_path_space
PASSED: modprobe_options_config_path_control
```

No unrelated failure, dirty fake-root state, loaded-module residue, or sanitizer finding occurred.

The package-style and exact-source behavior is:

```text
no-space configuration path: parent/nested marker counts 1/1
spaced configuration path:   parent/nested marker counts 1/0
parent status: 0
nested status: 0
```

The parent uses the requested configuration. An `install` command starts another `modprobe`; the parent serializes `-C` and its raw pathname into `MODPROBE_OPTIONS`; the child reparses a changed argument vector and can silently use another configuration.

## Transport design review

### V1 — legacy parser rewrite held

PR #2 changes raw-backslash behavior and does not bound recursive option growth. It remains execution history, not selected source.

### Narrow exact-record V2 held

PR #3 carries only generated `-C/-s/-q/-v` state. A reversing inherited-`-d` control proved current kmod can preserve additional private options that this design drops.

### Strict provenance rejected

PR #4 separates inherited state from exact generated state, but rejects an install script that mutates `MODPROBE_OPTIONS` by appending `-q`. Current kmod accepts that mutation for representable legacy values, so strict mismatch rejection is not recursively equivalent.

### Provenance fallback experiment

PR #5 tests a bounded fallback after exact metadata validates:

1. compare the actual legacy mirror with the expected inherited-plus-generated mirror;
2. when an install script changed the mirror, rebase the actual string as inherited state;
3. clear the exact generated suffix;
4. parse the rebased inherited state with the unchanged legacy parser;
5. publish it once to avoid later duplication;
6. continue to reject malformed exact/base records and positional exact records.

Local GCC 14.2 and Clang 17 ASan/UBSan multicall builds passed spaced recursive `-C` through three dependency-free levels, inherited `-d`, install-script `-q` mutation, repeated and clustered options, representable mixed-version direction, and safe malformed-state boundaries.

The first hosted fallback generation, run `30957536612`, did not execute source. The committed base64 text matched its digest, but the decoded gzip stream had CRC and length errors.

A recovery workflow now retains decompressed output despite the damaged trailer, then requires that output to pass `git apply --check`, materialize exactly 29 expected paths, format, build, and pass all focused/full/discriminator gates:

```text
head: 94c42b0374c5b668eaf8f31a8daf79da1b268be0
run:  31047684477
GCC:  92447161754
Clang:92447161730
latest observation: queued
```

If recovery succeeds, regenerate a clean carrier from the retained materialized patch. Do not preserve the damaged gzip stream as the final evidence carrier.

This remains an experiment. It cannot recover pathname identity after an old parent has already flattened an unrepresentable value.

## Separate empty `MODPROBE_OPTIONS` allocation defect

When `MODPROBE_OPTIONS` exists but is empty, exact `prepend_options_from_env()` calculates no independent string storage and then copies the terminating NUL. Hosted run `30957800012` reproduced under both GCC and Clang:

```text
AddressSanitizer: heap-buffer-overflow
WRITE of size 1
```

The ordinary non-sanitized Debian binary still exits successfully. No exploitability or security-severity claim is made.

PR #6 isolates a behavior-preserving repair:

- calculate pointer count and pointer bytes independently;
- calculate `envlen + 1` string bytes independently;
- use checked multiplication/addition;
- leave the legacy parser and raw-backslash behavior unchanged;
- add a native `MODPROBE_OPTIONS=""` test using `modprobe --version`.

The first hosted candidate generation applied cleanly with an exact two-file fence but stopped at clang-format because the new test initializer used the wrong closing-brace indentation. No candidate build ran.

That formatting owner was repaired, the old workflow was retired, and a simpler v2 gate was registered:

```text
head:       b55841035fc32a2231057edf94966b5786aca22e
patch hash: 27048a0feb47fc3ea70c8d905ebb5e97e76a30bd7b59e72039a7260c93ba3bf6
run:        31047564100
GCC:        92446754730
Clang:      92446754671
latest observation: queued
```

The v2 gate first requires exact baseline loss, then requires formatting, direct candidate success, the focused native test, complete suite, cleanup, and retained receipts.

This allocator repair is independent of the recursive transport policy and can be assessed on its own two-file fence.

## Overlap refresh

Fresh open issue and pull-request searches on current upstream found no matching implementation for:

- recursive `MODPROBE_OPTIONS` configuration-path identity with whitespace;
- explicitly empty `MODPROBE_OPTIONS` heap-buffer-overflow;
- `prepend_options_from_env()` allocation correction.

Searches can miss differently worded work. Refresh again immediately before any authorized public action.

## Stop rule

Do not select or publish a recursive transport repair until:

1. exact current-master GCC and Clang refresh is terminal;
2. the final native characterization remains attributable to unchanged product logic;
3. fallback recovery, focused rerun, full suite, and safe discriminator are terminal;
4. the damaged carrier is replaced with a clean reproducible source artifact;
5. mixed-version and install-script mutation limitations are documented honestly;
6. no temporary carrier remains in a selected source diff;
7. standard final-head CI is inspected;
8. overlap, contribution policy, and formal review state are refreshed.

Assess the empty-environment allocator repair separately. It does not require choosing a recursive transport policy.

## First incomplete steps

1. Inspect current-master run `31047887468`.
2. Inspect fallback recovery run `31047684477`.
3. Inspect empty-environment repair run `31047564100`.
4. If the fallback applies, regenerate a clean carrier from the retained materialized patch before further promotion.
5. If the allocator repair passes, retain exact baseline/candidate artifacts and consider a clean source-only candidate branch.
6. Do not contact upstream without explicit authorization.
