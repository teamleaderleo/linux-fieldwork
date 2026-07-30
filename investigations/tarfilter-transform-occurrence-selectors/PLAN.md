# Execution plan

1. Copy the exact imported `tarfilter` into `TemporaryDirectory`.
2. Apply the merged PR #68 integrated transform patch.
3. Run `s/a/b/2` against that predecessor and require rejection.
4. Apply the incremental occurrence-selector patch.
5. Compare the candidate and GNU tar for ordinary, global, numeric, zero, large-selector, flag-order, repeated-number, and case-insensitive cases.
6. Compare regular-member, hard-link-target, and symlink-target metadata for `s/a/b/2g`.
7. Run complete repository test discovery.
8. Record exact-head workflow IDs and any first failure in the investigation and issue #98.
9. Request exact-head review before merge.
10. Notify #36 and active LF-14 follow-ups with the bounded result and remaining grammar owners.
