# Current handoff

Updated: `2026-08-01 15:28 +08:00`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-07-file-mirror-confinement` |
| Linux Fieldwork technical head before this handoff commit | `9ac5fdab87f826df5742f593b4bc236053a98e88` |
| Canonical upstream repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap` / `main` |
| Canonical upstream head observed | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Controlled fork | `https://github.com/teamleaderleo/mmdebstrap` |
| Fork base | `master@574048f2a720057b75e56622003932f344dc700a` |
| Candidate branch | `linux-fieldwork/unit-07-file-mirror-confinement` |
| Candidate head | `8b8dce6910badeda1e72e28f471fa220a22eea7d` |
| Candidate commits | setup `b18095f0a9916ad70872f6740ffae033fda9b034`; cleanup `8b8dce6910badeda1e72e28f471fa220a22eea7d` |
| Candidate setup Git blob | `80bf3f3ef4f5535ca802d91ac8bc6f3c2999a70c` |
| Candidate cleanup Git blob | `30ff2c56d83b5bedd91ec62e65f4c6a18bd4a6f6` |
| Candidate setup SHA-256 | `f750be95ada2a3e39c972653158092f907f153ff0ca07c2200a326bcc11920be` |
| Candidate cleanup SHA-256 | `867443a4fd2737f5275c11180f1f17d6f7bc92d487e476327834764c06a8afc7` |
| Packet patch | `patches/0001-file-mirror-automount-containment.patch` |
| Packet patch SHA-256 | `928533ff01be39ba66c5350f7951706fd7f017448449c2671bb95a271db75f25` |
| Reusable matrix | `scripts/test_candidate_hooks.py` |
| Matrix script SHA-256 | `a3da8cd22454e1f42b9328ad1f3cc0c372062b668e97e815a48aa160cdc166a0` |
| Latest hosted result | historical Linux Fieldwork run `30580904313` / job `91000593721`, success at PR #179 head `6db473c5e3e462a93f9ba0bc975dbc46164f863b`; no status attached to fork candidate head |

The branch head after this file is written is the handoff commit itself. The table preserves the exact technical-content parent.

## Current bounded claim

The controlled fork baseline exactly matches the packet baseline. The composed candidate is committed on a concrete fork branch with a complete two-file diff, zero base drift, exact candidate hashes, successful shell syntax, and a fresh 10-check disposable fake-command matrix. The GitHub fork is a controlled test carrier. The canonical Forgejo repository remains the intended upstream source owner.

## Work completed in this pass

- located `teamleaderleo/mmdebstrap` and confirmed owner-level write access;
- identified fork default branch `master` and base head `574048f2a720057b75e56622003932f344dc700a`;
- fetched both fork hooks and confirmed their Git blobs equal the packet baseline;
- created fork branch `linux-fieldwork/unit-07-file-mirror-confinement`;
- committed the setup candidate at `b18095f0a9916ad70872f6740ffae033fda9b034`;
- committed the cleanup candidate at `8b8dce6910badeda1e72e28f471fa220a22eea7d`;
- reviewed the complete fork comparison: two commits ahead, zero behind, exactly two changed hook paths;
- reconstructed the committed candidate bytes and verified the packet SHA-256 receipts;
- ran `/bin/sh -n` on both hooks;
- ran a fresh 10-check fake-command matrix covering setup, cleanup, correction, and immediate rerun;
- added reusable matrix script `scripts/test_candidate_hooks.py` to the packet;
- updated `README.md`, `TESTS.md`, `DECISIONS.md`, and this handoff;
- opened no pull request and contacted no upstream maintainer.

## Changed paths

### Controlled fork

- `hooks/file-mirror-automount/setup00.sh`
- `hooks/file-mirror-automount/customize00.sh`

### Linux Fieldwork packet

- `upstream-packets/units/07-file-mirror-confinement/README.md`
- `upstream-packets/units/07-file-mirror-confinement/TESTS.md`
- `upstream-packets/units/07-file-mirror-confinement/DECISIONS.md`
- `upstream-packets/units/07-file-mirror-confinement/HANDOFF.md`
- `upstream-packets/units/07-file-mirror-confinement/scripts/test_candidate_hooks.py`

## Distinguishing observations

- The fork is a GitHub mirror with default branch `master`, while the canonical repository remains Forgejo `main`.
- Fork baseline hook blobs exactly equal the packaged and Linux Fieldwork imported blobs, so no fork-specific source adaptation was required.
- The candidate branch comparison contains only the two intended hook files.
- Exact committed candidate bytes equal the packet composition hashes.
- The reusable matrix returned 10 successful checks:
  - shell syntax;
  - traversal rejection;
  - filesystem-root refusal;
  - ordinary repository mapping;
  - terminal source-symlink URI reachability;
  - parent-component rejection;
  - local package confinement;
  - root cleanup preflight, correction, and immediate rerun;
  - fakechroot cleanup preflight, correction, and immediate rerun;
  - cleanup symlink-escape rejection.
- GitHub reported no combined status checks on candidate head `8b8dce6910badeda1e72e28f471fa220a22eea7d`.

## Gates completed

- controlled fork discovery and permission check;
- exact fork base identification;
- baseline blob equality check;
- controlled branch creation;
- candidate source commits;
- complete two-file comparison review;
- exact candidate hash verification;
- shell syntax;
- reusable disposable matrix;
- cleanup and immediate rerun checks in root and fakechroot modes;
- packet identity, test, decision, and handoff updates.

## Red or neutral runs classified

- The first branch-creation attempt using a raw commit SHA was blocked by the connector safety classifier before GitHub received it. Retrying from the named base ref `master` succeeded. This was a connector classification event, not a repository or source failure.
- The first disposable matrix run found a fake-`rm` log expectation mismatch after earlier cases passed. The harness log parser was corrected, and the complete matrix was rerun from a fresh temporary directory successfully.
- A later reusable-script execution emitted unrelated spreadsheet-runtime warmup text on stderr while returning exit `0` and the expected JSON receipt. The hook test process itself passed; the stderr belongs to the host Python environment startup.

## Cleanup state

No real mounts, unmounts, sockets, listeners, namespaces, containers, package mutations, or external repository submissions were created. Temporary roots and fake command logs were removed by `TemporaryDirectory`. Intentional retained state consists of the controlled fork branch, its two commits, the Linux Fieldwork unit branch, packet patch, matrix script, and evidence records.

## First incomplete step

Run the reusable matrix from actual local checkouts of the controlled fork candidate head and Linux Fieldwork packet branch, retaining the command output with both repository heads in one receipt. Then attach or run a hosted status on the exact fork head if the repository supports it.

## Next safe action

```text
git -C mmdebstrap checkout 8b8dce6910badeda1e72e28f471fa220a22eea7d
git -C linux-fieldwork checkout upstream/unit-07-file-mirror-confinement
python3 \
  linux-fieldwork/upstream-packets/units/07-file-mirror-confinement/scripts/test_candidate_hooks.py \
  --setup mmdebstrap/hooks/file-mirror-automount/setup00.sh \
  --cleanup mmdebstrap/hooks/file-mirror-automount/customize00.sh
```

Record both `git rev-parse HEAD` values, exact stdout, exit status, cleanup state, and immediate rerun in `TESTS.md`.

After that, test the packet patch against a fresh canonical Forgejo tree at `77ec9be5417ee44c96343d2347145585da1b1f94`, perform the final overlap search, and review the complete upstream-facing diff.

## Unresolved blockers

- technical: hosted exact-head status and canonical-tree apply remain;
- compatibility: maintainer acceptance of GNU `realpath -m -s`, full marker preflight, and rejection of legacy leading-slash markers remains unknown;
- overlap: run one final current search immediately before authorization;
- environment or tooling: the current runtime could not clone GitHub because DNS/network access was unavailable, so connector writes and locally reconstructed exact bytes were used;
- authority: upstream pull request, issue, comment, email, review, or other public contact requires explicit authorization.

## Files to read first

1. `README.md`
2. `TESTS.md`
3. `scripts/test_candidate_hooks.py`
4. `SOURCE_MAP.md`
5. `DEEP_DIVE.md`
6. `DECISIONS.md`
7. issue #164 and PR #179

## External-contact state

`false; none occurred`. The controlled fork branch and commits were created under the user's explicit authorization to try the update against the fork. No pull request or communication was created.

## Do not repeat

- Do not canonicalize the host source and reuse it as the in-root destination; terminal source-symlink URIs break.
- Do not allow embedded `..` solely because normalization stays inside the root; the configured URI can remain unreachable.
- Do not validate and act on marker entries sequentially; later invalid entries can cause partial cleanup.
- Do not describe the GitHub mirror as the canonical upstream repository.
- Do not create a pull request or contact upstream without explicit authorization.
