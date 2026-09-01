# Recursive modprobe repair decision

## Decision

Use an **issue-first upstream path** and continue the source work as a **reconstructed provenance-aware successor**, not as a rewrite of the existing legacy `MODPROBE_OPTIONS` grammar.

No upstream issue or pull request is posted by this decision record.

## Why

The recursive configuration-identity defect is proven on current upstream source. The remaining uncertainty is not whether the bug exists; it is how to preserve compatibility while fixing the transport.

The explored designs establish useful boundaries:

- Parser-rewrite v1 fixes generated whitespace but changes existing raw-backslash behavior and leaves recursive growth unbounded.
- Narrow exact-record v2 preserves generated values but drops inherited private options such as `-d`.
- Strict provenance preserves inherited and generated state but rejects install-script mutation of `MODPROBE_OPTIONS` that current kmod accepts.
- Provenance fallback is the first design that addresses generated argv identity, inherited state, install-script mutation, and recursive duplication together. Its original committed source carrier is damaged, so it must not be represented as recoverable source.

## Selected engineering direction

Reconstruct the fallback mechanism from a clean, reviewable source base and label it as reconstructed work.

The successor should:

1. leave the existing legacy parser unchanged for inherited `MODPROBE_OPTIONS` input;
2. carry kmod-generated recursive option state with explicit argument boundaries;
3. distinguish inherited legacy state from kmod-generated state;
4. preserve inherited private options rather than narrowing propagation to only `-C/-s/-q/-v`;
5. tolerate valid install-script mutation by rebasing the changed legacy mirror as inherited state after metadata validates;
6. prevent previously generated options from being duplicated at every recursive level;
7. fail visibly on malformed exact metadata rather than silently changing argv;
8. document the mixed-version limit: a new child cannot recover pathname identity after an old parent has already flattened an unrepresentable value.

## Base policy

Do not build the successor on the July snapshot merely because the investigation started there. Upstream master has advanced to `dae6c02ffed2e8d16da8dba16d974fc955eebb1f` and the relevant mechanism remains present.

Before materializing product source in the owned fork, synchronize a clean branch to the then-current upstream master and repeat the source/overlap refresh.

## Required gate

A candidate is not ready for an upstream pull request until one exact source head passes:

- the existing losing baseline as a reversing control;
- spaced and no-space recursive `-C` identity;
- at least three dependency-free recursive levels with bounded environment state;
- inherited `-d` behavior;
- install-script `MODPROBE_OPTIONS` mutation;
- repeated and clustered options;
- malformed exact-state rejection;
- mixed-version representable/unrepresentable controls;
- GCC and Clang ASan/UBSan builds;
- focused native tests twice;
- complete native suite;
- standard final-head CI;
- clean source and cleanup receipts.

## Publication sequence

1. Finalize the compact upstream issue text and refresh duplicate searches.
2. Post the issue only when external contact is explicitly authorized.
3. Use the issue discussion to confirm compatibility expectations if maintainers have a preference.
4. Open a source pull request only after the reconstructed candidate satisfies the gate above.

## Separate lane

The explicit-empty `MODPROBE_OPTIONS` allocation overflow is independent. Keep its minimal allocator fix and tests separate from the recursive transport issue and patch.
