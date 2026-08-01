# Handoff — unit 16

## Current state

State: `ACTIVE`  
Linux Fieldwork branch: `upstream/unit-16-tarfilter-type-hardlinks`  
Internal draft PR: #399  
External-contact state: unauthorized; none made

The packet has been created and filled. The branch retains a packet-local composed predecessor, an executable two-case final-name characterization, exact carrier identities, test commands, design decisions, and withheld upstream drafts.

## Exact heads and identities

| Item | Identity |
| --- | --- |
| Linux Fieldwork base | `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Technical characterization head | `ac21c095faae34fcd3cec3e4a7beae5a83979fe1` |
| Latest packet head before this handoff commit | `f8d940bf73dff006fbb5db6c2c93490bde254ace` |
| Imported tarfilter blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Transform/strip patch blob | `1703984aa0c030e5131618a3541ee85bfd68ec65` |
| PR #248 head | `f1b013832b5f3b073a9131de83ce89077771a7ea` |
| PR #310 head | `32dfa36a6feb533bc1126a11ef33979e45b410ec` |
| Packet predecessor patch commit | `0a79e81085d6769387f314ad1ead0ad2274c2616` |
| Focused test commit | `ac21c095faae34fcd3cec3e4a7beae5a83979fe1` |

The branch tip after this file is the commit returned by the GitHub contents write; use the branch ref as the packet head.

## Completed work

1. Read issue #397, packet workflow README, packet index, and the direct canonical carriers for unit 16.
2. Read the executed baseline PR #244 and canonical transform/strip PR #68.
3. Claimed unit 16 on issue #397.
4. Created `upstream/unit-16-tarfilter-type-hardlinks` from current `main`.
5. Opened internal draft PR #399 to obtain pull-request CI.
6. Retained `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch`.
7. Added `tests/test_tarfilter_type_excluded_final_name_identity.py`.
8. Encoded both issue #335 strip discriminators:
   - valid final target falsely rejected;
   - missing final target falsely accepted.
9. Required zero-fuzz two-patch application, Python compilation, emitted member maps, finalized partial output, GNU tar extraction, and inode identity controls.
10. Filled README, source map, deep dive, tests, decisions, withheld upstream drafts, and this handoff.

## Latest distinguishing evidence

### Source and carrier evidence

PR #310 records retained state under normalized input identity and checks a hard-link target before strip and transform rewriting. PR #68 rewrites both emitted member names and hard-link targets. The two operations therefore use different identity domains.

### Prepared executable evidence

At technical head `ac21c095faae34fcd3cec3e4a7beae5a83979fe1`, the focused test requires:

- false rejection: status 1 and partial `{base: REGTYPE}` while a direct `{base, peer -> base}` archive extracts with one inode;
- false acceptance: status 0 and `{peer: LNKTYPE -> root/base}` followed by GNU tar extraction failure.

### CI state

- Linux Fieldwork CI run `30674423172` / run 1100 was queued for exact technical head `ac21c095faae34fcd3cec3e4a7beae5a83979fe1`.
- Linux Fieldwork CI run `30674597791` / run 1107 was queued for packet head `f8d940bf73dff006fbb5db6c2c93490bde254ace`.
- At handoff creation, `lab-tools` remained queued and the unrelated jobs were skipped.

Treat the characterization as prepared until one exact technical-head run completes and its job logs are reviewed.

## Cleanup state

No local repository clone survived; the container could not resolve GitHub during direct clone. All durable work lives on the Linux Fieldwork branch and PR #399.

The committed test uses `TemporaryDirectory` for patched sources, archives, and extraction trees. It creates no persistent process, socket, mount, lock, package mutation, device node, or external network activity.

## First incomplete step

Inspect Linux Fieldwork CI run `30674423172`. When `lab-tools` completes, fetch its job steps and logs. Confirm that:

```sh
python3 -m unittest tests.test_tarfilter_type_excluded_final_name_identity -v
```

ran on exact head `ac21c095faae34fcd3cec3e4a7beae5a83979fe1` and both characterization tests passed.

If patch application fails, repair only `patches/0001-compose-pr310-predecessor-on-transform-carrier.patch` against the canonical PR #68 patch and rerun. If assertions differ, record the exact emitted map, status, stderr, and GNU tar result before changing the expected mechanism.

## Next safe technical action

After exact characterization passes:

1. extract one shared name-rewrite helper from the PR #68 carrier that returns either a final identity or a dropped result;
2. use member-name scope to project type-excluded names;
3. use hard-link scope to project retained hard-link targets before dependency checking;
4. keep original names for the diagnostic;
5. add red-to-green assertions for both strip cases;
6. add transform-scope and output-name collision controls;
7. rerun inherited PR #248 and PR #310 matrices, cleanup, immediate rerun, and the complete gate.

## Selected invariant

A retained hard link is valid when its final rewritten target identity is already available among emitted final member identities. A type-excluded occurrence marks its projected final member identity unavailable only when no retained occurrence supplies that target. Rejection occurs before writing the broken hard-link member and after allowing the tar context to finalize.

## Open questions

- Whether final availability needs occurrence counts instead of sets once transform collisions are introduced.
- How a type-excluded member whose projected identity is dropped by component stripping should affect state; the likely result is no unavailable emitted identity.
- Whether diagnostics should include both original and final target spellings when they differ.
- Current upstream destination, base branch, and controlled fork.

## Tests still required

- exact technical-head focused CI result and logs;
- immediate focused rerun;
- transform scope controls for member versus hard-link target projection;
- duplicate/output-name collision controls;
- inherited PR #248 and PR #310 matrices;
- complete current-main gate on the selected correction;
- package pipeline, other extractors, platforms, and privileged metadata where later authorized and useful.

## External-contact guard

Do not open or comment on any external upstream issue, pull request, merge request, mailing list, email thread, package tracker, or release channel without explicit authorization. Internal Linux Fieldwork work and issue #397 checkpoints remain authorized.
