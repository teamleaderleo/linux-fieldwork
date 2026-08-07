# Compiled exact-option transport prototype receipt

## Environment

- Date: 2026-08-05
- Host compiler 1: GCC 14.2.0
- Host compiler 2: Clang 17.0.0
- Sanitizers: AddressSanitizer and UndefinedBehaviorSanitizer
- Optimization/debug: `-O1 -g -fno-omit-frame-pointer`
- Warning gate: `-Wall -Wextra -Werror`
- kmod source modified: no
- Kernel modules inserted or removed: no

## Files

- Prototype: `prototype_exact_option_transport.c`
- Runner: `run_exact_option_transport_v2.sh`
- Normalized result: `artifacts/exact-option-transport-c.json`

## SHA-256

```text
prototype source: fdeb913c605f5009d544d5b7f8c643835b4ebfad02eab21be4c9af7fc868812b
runner:           ed44cd1d6092935bca0c9dd8e5cd49f376e68576c58347270315c7b24f6adac3
result:           ae8dbce2e9bcbbc4b4f54dc1ca5ebe790ea2659f0c56c05570485f2bb6065a73
gcc binary:       9254649b2f1127715191b7d88018fe0c83a80ae853d977a266d016f78cf4c275
clang binary:     33156f4891ecaebd4881a85c3cd11b7d70d18e61e33e5766bfc97c63b7ef456f
```

GCC and Clang emitted byte-identical JSON.

## Established

- 10,007 generated non-NUL byte-string arguments round-trip through the length-delimited record.
- Nine malformed/non-canonical records are rejected.
- The modeled current legacy parser preserves a raw backslash when no exact record exists.
- A legacy quoted space-bearing path remains a passing control.
- Five exact arguments occupy 39 record bytes and remain unchanged through 20 decode/rebuild levels.
- Under the model's current precedence rule, `KMOD1;` is a valid empty authoritative vector.

## Decision-changing negative result

The proposed escaped legacy mirror does **not** preserve exact argv for an older child using the current parser. Therefore the Python model's statement that the legacy mirror is non-authoritative is insufficient for mixed-version recursion: an old child has no exact-record decoder and necessarily treats the mirror as authority.

This does not invalidate the exact record mechanism. It requires an explicit mixed-version policy and tests before integrating it into kmod.

## Evidence boundary

This is compiled mechanism evidence, not a kmod source repair. It does not establish:

- integration with `getopt_long()` provenance;
- install/remove behavior through `system()`;
- new-parent/old-child compatibility;
- old-parent/new-child compatibility;
- an acceptable environment-variable name or public contract;
- behavior at platform environment-size limits;
- maintainer acceptance.
