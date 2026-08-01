# Current handoff

Updated: `2026-07-31 17:07 PDT`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-07-file-mirror-confinement` |
| Linux Fieldwork technical head before this handoff-only commit | `912695178ee0c2b8d1b1e96f544e720543a7c252` |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap` / `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Candidate fork/branch | `NEEDS FORK`; no external fork created |
| Candidate head | packet patch SHA-256 `928533ff01be39ba66c5350f7951706fd7f017448449c2671bb95a271db75f25` |
| Patch or series | `patches/0001-file-mirror-automount-containment.patch` |
| Owning issue/PR | Linux Fieldwork issue #164 / merged PR #179; priority unit #397 unit 07 |
| Latest workflow/run/artifact | historical exact-head CI `30580904313` / job `91000593721`, success at PR #179 head `6db473c5e3e462a93f9ba0bc975dbc46164f863b`; packet-branch CI pending |

The branch head after this file is created is the handoff commit itself. The table records the exact technical-content parent so a worker can distinguish packet work from the handoff-only commit.

## Current bounded claim

Against the current mmdebstrap hook source identity, the retained three-patch Linux Fieldwork candidate composes cleanly into one upstream-path patch. The final scripts pass POSIX shell syntax. Historical exact-head CI proves the full disposable fake-action behavior for the same final source contract. Packet-exact execution of that matrix and hosted CI on the unit branch remain pending.

## Work completed in this pass

- read issue #397, packet workflow README/index, issue #164, PR #179 and its review history, and the linked adjacent carriers #153/#158, #79/#90, and #53;
- posted `CLAIMED — unit 07` on issue #397;
- created `upstream/unit-07-file-mirror-confinement` from `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`;
- identified canonical upstream `main@77ec9be5417ee44c96343d2347145585da1b1f94`;
- confirmed the current packaged setup and cleanup blobs equal the Linux Fieldwork imported blobs;
- applied local patches 0001, 0002, and 0003 in order to exact baseline bytes;
- generated one fresh upstream-path patch from baseline to final candidate;
- recorded patch and candidate source hashes;
- ran `/bin/sh -n` successfully on both final scripts;
- wrote the canonical packet overview, source map, deep dive, test receipts, decision log, public drafts, patch, and this handoff;
- made no external contact.

## Changed paths

- `upstream-packets/units/07-file-mirror-confinement/README.md`
- `upstream-packets/units/07-file-mirror-confinement/SOURCE_MAP.md`
- `upstream-packets/units/07-file-mirror-confinement/DEEP_DIVE.md`
- `upstream-packets/units/07-file-mirror-confinement/TESTS.md`
- `upstream-packets/units/07-file-mirror-confinement/DECISIONS.md`
- `upstream-packets/units/07-file-mirror-confinement/UPSTREAM_ISSUE.md`
- `upstream-packets/units/07-file-mirror-confinement/UPSTREAM_PR.md`
- `upstream-packets/units/07-file-mirror-confinement/patches/0001-file-mirror-automount-containment.patch`
- `upstream-packets/units/07-file-mirror-confinement/HANDOFF.md`

## Distinguishing observations

- The current official repository head is newer than Debian `1.5.7`, yet the hooks directory still reports the March 2024 file-mirror warning-prefix commit as its latest relevant change.
- Current packaged hook blobs exactly match the imported Linux Fieldwork blobs: setup `6ccbdaf2ba97c77c4e5223ac5280acd51a998424`, cleanup `b6b9b46afdd9dad01df3abcb514475326162e42c`.
- No semantic source rebase edit was required.
- Local patch 0003 applies with one line of fuzz after patch 0002 shifts helper context. The packet patch is a fresh final diff, so upstream application does not depend on that fuzz.
- The three local increments belong in one final upstream unit because setup writes the marker authority and cleanup consumes it.
- Package-test scheduling and HTTP readiness carriers share environment context but have no file overlap with this candidate.

## Gates completed

- carrier and adjacent-lane read-through;
- current upstream repository/base identification;
- packaged-source blob equality check;
- ordered local patch application;
- fresh composed patch generation;
- composed patch SHA-256 receipt;
- candidate setup and cleanup SHA-256 receipts;
- `/bin/sh -n` for setup and cleanup;
- scope/overlap classification;
- public draft preparation;
- cleanup inventory.

## Red or neutral runs classified

- No red hosted run occurred in this pass.
- Patch 0003 reported `Hunk #1 succeeded ... with fuzz 1`; this is a successful incremental application with shifted context, classified as neutral for source semantics and removed from the final artifact by regenerating the composed diff.
- Historical carrier failures and repairs are classified in issue #164 and PR #179; the final exact-head run is green.

## Cleanup state

No real mounts, unmounts, sockets, listeners, containers, package mutations, or external repository writes were created. Disposable patch-composition files lived only in the ephemeral tool runtime. Intentional retained state consists of the Linux Fieldwork unit branch, packet records, and composed patch.

## First incomplete step

Run the complete five-file fake destructive-command matrix against the single packet patch, rather than against the historical three-patch investigation paths.

## Next safe action

From a checkout of the unit branch, add a focused packet-patch equivalence regression or temporarily point the five existing fixtures at the packet patch, then execute:

```text
python3 -m unittest \
  tests.test_file_mirror_automount_containment \
  tests.test_file_mirror_automount_root_guard \
  tests.test_file_mirror_automount_cleanup_preflight \
  tests.test_file_mirror_automount_source_normalization \
  tests.test_file_mirror_automount_parent_component_reachability
```

Record the exact command, branch head, test count, result, cleanup, and immediate rerun in `TESTS.md`. Then review the complete packet diff and move to `READY FOR AUTHORIZATION` only when hosted CI is green at the exact head.

## Unresolved blockers

- technical: packet-exact fake-action matrix and second fresh-tree apply remain;
- compatibility: upstream acceptance of GNU `realpath -m -s` and fail-closed legacy markers remains unknown;
- overlap: no active equivalent upstream issue or pull request was found in the visible six open issues; conduct one final search immediately before authorization;
- environment or tooling: canonical Forgejo archive bytes were not downloaded into the local runtime, so exact-current-base application is supported by repository history plus matching packaged blobs rather than a local archive hash;
- authority: external fork, issue, pull request, comment, email, or review requires explicit authorization.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. issue #164 and PR #179, including final review comments

## External-contact state

`false; none occurred`. The only public action in this pass was the authorized internal Linux Fieldwork claim comment on issue #397.

## Do not repeat

- Do not canonicalize the host source and reuse that spelling as the in-root destination; it breaks terminal source-symlink URIs.
- Do not allow embedded `..` merely because lexical normalization stays inside the root; the original URI may remain unreachable.
- Do not validate and act on cleanup entries sequentially; a later invalid entry can cause partial cleanup.
- Do not split setup and cleanup without an explicit temporary-risk argument; they share the marker authority contract.
- Do not rerun the historical three-patch matrix and describe it as packet-patch evidence without first switching the fixture to the composed patch.
- Do not create a fork or contact mmdebstrap upstream without explicit authorization.
