# Provenance-aware recursive option handoff

## State

- Investigation: recursive `modprobe` configuration identity
- Disposition: `HOLD — baseline/native proof complete; v1/v2 blocked; provenance-aware v3 executing`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork head before this commit: `ddc75ad71720d0112471cba5bd8da2fcaae33cdd`
- Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#412`
- Exact public/fork kmod base: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Native characterization: `teamleaderleo/kmod#1@84ba8ae9db4f455965efa22afdd5cb177781106b`
- Candidate v1: `teamleaderleo/kmod#2` — held for raw-backslash compatibility and recursive growth
- Candidate v2: `teamleaderleo/kmod#3` — held because rebuilding only `-C/-s/-q/-v` drops inherited private options such as `-d`
- Provenance-aware v3: `teamleaderleo/kmod#4@677468029ddc0a718824060f1b1e083a2518d41b`
- Formal reviews: none
- External contact: unauthorized; none made

## Closed evidence

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

## Why v1 and v2 remain blocked

### V1

V1 changes existing raw-backslash parsing:

```text
-C /foo\bar
current:   /foo\bar
v1:        /foobar
```

It also does not bound inherited-option duplication across recursive levels.

### V2

V2 keeps the legacy parser unchanged and carries a separate exact record, but it rebuilds only `-C/-s/-q/-v`.

A safe reversing control used inherited `MODPROBE_OPTIONS=-d $TMP/root` and a nested `--show-depends` lookup. Current kmod preserved `-d` and found the custom module root; v2 dropped `-d`, searched the host module directory, and failed. Candidate v2 is therefore not recursively equivalent.

## Provenance-aware v3 mechanism

V3 separates recursive state into:

1. an inherited private-string base preserved byte-for-byte;
2. a versioned, length-delimited exact record for generated recursive arguments;
3. a base-length field identifying the inherited prefix in the compatibility mirror.

Each invocation parses the inherited base with the unchanged legacy parser, decodes the prior generated exact suffix separately, derives newly selected CLI `-C/-s/-q/-v` options, and republishes the fixed base plus the generated suffix once.

New children use the exact generated suffix and ignore the generated mirror. Old children receive the unchanged base plus a representable generated mirror. Unrepresentable new-to-old handoffs receive an explicit sentinel and fail visibly.

Exact records accept only deliberately generated recursive options. Empty generated state is authoritative. Malformed and positional records fail closed.

## Exact v3 carrier

Owned-fork draft PR: `teamleaderleo/kmod#4`

Branch/head at creation:

```text
experiment/modprobe-exact-option-provenance
677468029ddc0a718824060f1b1e083a2518d41b
```

Carrier files only:

- `.github/modprobe-exact-option-provenance.patch.gz.b64`
- `.github/test-modprobe-option-provenance.py`
- `.github/workflows/validate-exact-option-provenance.yml`

Product source is not committed.

Exact identities:

```text
base tools/modprobe.c blob:
413960cae0f39945a3f2d6509dc4a8c262ae2609

reconstructed patch SHA-256:
caed53a3a7f5dc57f2d4114da21a623dfd9ea1343881bdced3617adf30ecee32

compressed patch SHA-256:
ae01646901a5bc8305a4869446344022e21be420414ab6074fa1e2a7a5be75bd
```

The materialized source/test patch has an exact 28-file fence covering `tools/modprobe.c`, `testsuite/test-modprobe.c`, `scripts/setup-rootfs.sh`, policy fixtures, three-level recursion fixtures, and inherited-`-d` fixtures.

## Local compiled v3 evidence

The exact patch was applied to the archived exact base and assembled into complete multicall kmod binaries under GCC 14.2 and Clang 17 with ASan/UBSan.

Both toolchains passed:

- no-space and spaced direct/nested configuration identity;
- inherited base plus exact generated suffix;
- authoritative empty generated suffix;
- malformed and positional exact-record rejection;
- unchanged raw-backslash fallback;
- inherited `-d` reaching a nested `--show-depends` child;
- attached short `-C/path`;
- attached long `--config=path`;
- options after a non-option;
- clustered `-qv`;
- repeated `-C` ordering;
- stable inherited-base, exact-record, and mirror lengths through three real recursive levels;
- representable new-parent/old-child recursion;
- visible failure for an unrepresentable new-parent/old-child pathname;
- expected unrecoverable old-parent/new-child pathname loss.

No real module insertion/removal or sanitizer finding occurred in the safe matrices.

Exact local v3 binary hashes:

```text
GCC:
6c9bd47452df9d293a17a66b72e7944eabe7d8bf2d0a6590357babf62ed454a9

Clang:
9a6e5ca79e5aad031595fba863aa17b8ccabfdffaded39ed74658c6d61d9ca7f
```

The supplemental CLI/mixed-version discriminator passed both binaries. Compiler-specific source-line numbers in one old-child diagnostic are the only textual difference after normalizing paths and binary names.

## Separate exact-current memory finding

Exact current source has a separate one-byte heap write beyond its allocation when `MODPROBE_OPTIONS` is explicitly set to an empty string, including `modprobe --version`.

GCC and Clang ASan both reproduce it. V3 treats an explicitly empty inherited base as zero arguments and adds a native regression, but this memory finding must remain separately identifiable from the recursive pathname policy. No exploitability or security-severity claim is made.

## Hosted state

PR #4 is open, draft, and mergeable.

Registered validation run for head `677468029ddc0a718824060f1b1e083a2518d41b`:

```text
Validate exact option provenance: 30938595336
```

At the latest observation the GCC and Clang jobs were queued. The workflow is read-only, verifies exact ancestry and patch hashes, applies the patch only in the runner, runs the focused native suite twice plus the complete suite, executes the supplemental discriminator, restores the carrier tree, and uploads receipts.

Queued or cancelled work is not product evidence.

## Stop rule

Do not select or publish a repair until:

1. the provenance workflow is terminal under GCC and Clang;
2. its exact patch and 28-file fence are retained;
3. focused reruns and the complete native suite pass without sanitizer findings;
4. the empty-environment regression is classified separately;
5. mixed-version limitations are documented honestly;
6. temporary carriers are absent from one exact final source diff;
7. standard final-head CI is inspected;
8. overlap, contribution policy, and review state are refreshed immediately before any authorized publication decision.

## First incomplete step

Inspect run `30938595336` and classify the first failing owner if red. If green, retain exact artifacts and compare the hosted supplemental result with the local GCC/Clang receipts. Do not materialize product source or contact upstream without explicit authorization.
