# Twenty-fifth pass — exact FEX-2608 revoked-H runtime

The ACTIVE -> REVOKED -> ACTIVE synthetic-H state machine has now passed the full integrated reduced matrix on exact FEX-2608 source `e869aa644a16e4332cdc15c1ea0b4d13d482385d`, the revision used by the original Apple M5 workload.

Owned-FEX branch: `ci/thunk-revoked-h-fex2608-20260814`.
Carrier commit: `0caf09699be6f12f075e3aceff13332b65728005`.
Workflow run: `31771462013`.
Artifact: `9208347298`, `thunk-revoked-h-fex2608-31771462013`.

The workflow completed successfully and retained the same four passing cases as current source:

```text
forced-different reload
same-address ABA
cross-thread hot-cache retirement
simultaneous same-H compatible owner promotion
```

The forced-different stale-H path exercises the revoked CustomIR definition before the expected guest fault, then later activation of the same H against generation 2 succeeds. The independent stale callback path remains controlled by the callback tombstone, and fresh/current callbacks remain healthy.

This means the current strongest reduced research candidate is now directly runtime-validated on exact FEX-2608, including coherent all-thread retirement and the revoked synthetic-H state rather than only the earlier delete/rebind mechanism.

The original M5 immediate final caller remains uncaptured; this exact-revision result establishes mechanism compatibility, not that last workload-specific edge.

No upstream FEX interaction was performed.