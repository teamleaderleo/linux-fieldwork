# Peer process notes: systemd and libarchive

Date: 2026-08-03

Scope: extract review and delivery habits from recently accepted work in the same subsystems, then apply them only inside controlled `teamleaderleo/*` repositories.

No public upstream contact is authorized by this note.

## systemd process observed

Recent merged oomd/Varlink work is usually narrow in feature scope but broad in review depth. Reviewers do not stop at the successful transition. They inspect:

1. callback object lifetime and explicit ref/unref ownership;
2. every early return and asynchronous disconnect path;
3. whether a failed allocation or parse leaves source and effective state divergent;
4. whether rollback is atomic rather than best-effort;
5. whether stale connections can mutate current-generation state;
6. whether event sources, timers, and Varlink userdata survive or disappear at the intended boundary;
7. style, Coccinelle, test placement, rebase state, and commit-message quality.

### Applied to fieldwork #140

Keep the work split into reviewable lanes:

- immutable current-main reproduction and reporter trace;
- executable policy/lifecycle model;
- standalone C reducer with focused unit tests;
- source-precedence integration prototype;
- connection-generation and first-message snapshot integration only after reducer semantics compile and pass.

Before promotion, require an exact-head receipt and answer each of these questions:

- Who owns every reporter, contribution, effective tuple, copied rule string, event source, and Varlink reference?
- What is removed on current disconnect, stale disconnect, empty snapshot, parse failure, allocation failure, and daemon shutdown?
- Can a rejected update change either source state or effective state?
- Can an older connection update or withdraw a newer generation?
- Does an identical snapshot preserve timing state?
- Does authority fallback restore the lower-ranked complete tuple without mixing fields?

Current status: no attached PR-run receipt was returned for the standalone reducer head `0209288b36f9368b43ed482a667810a7e0eb437c` or lifecycle-model head `7d9935aa2edb603507749ebb4f23d073c786476d` during this check. They remain unverified, not green.

## libarchive process observed

Recent accepted work favors deterministic in-tree tests located beside the existing format tests. A regression may be introduced first, but a proposed product change is expected to finish as one coherent review unit with the ordinary build/test matrix green. Maintainer feedback is often direct: add the missing deterministic case, keep the patch narrow, and rerun the normal matrix.

For issue #3314, the stated test target is:

- preserve an in-range inode where policy permits;
- replace overflow inode values with in-range values;
- keep replacements unique;
- maintain hardlink identity.

The existing odc writer is the nearest project-local precedent: it synthesizes archive inode values and maintains an identity map rather than hashing and risking collisions.

### Applied to fieldwork #409

The native newc regression on `teamleaderleo/libarchive#3` was strengthened at head `6ecf4acfe51ec4cca2d96c9e92a39ba47551ecff` to cover:

- exact ordinary in-range inode `1`;
- two distinct overflow identities on one device;
- repeated hardlink identity stability;
- the same inode on another device as a distinct key.

The proposed mapping key is the complete source identity `(devmajor, devminor, inode)`, not inode alone.

The implementation review must explicitly address the streaming constraint: once a header is emitted, a later in-range inode cannot force an earlier synthetic value to be rewritten. A candidate must therefore state which entries are synthesized, how zero/trailer is reserved, how exhaustion is reported, and why hardlink collisions cannot occur.

## Delivery rules copied into our process

- Test the public behavior, not only an internal helper.
- Keep expected-red evidence separate from claims of a fix.
- Never label queued, missing, or merge-derived receipts as exact-head success.
- Prefer an existing subsystem mechanism over a new framework.
- Record the first concrete compiler/test failure and patch that failure directly.
- Keep unrelated cleanup out of the product branch.
- Do not contact public upstream without explicit authorization.
