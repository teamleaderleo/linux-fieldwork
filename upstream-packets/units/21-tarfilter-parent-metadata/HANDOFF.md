# Current handoff

Updated: `2026-07-31 17:15 PDT`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-21-tarfilter-parent-metadata` |
| Linux Fieldwork head | this handoff commit; exact final SHA is recorded in the unit checkpoint on #397; substantive parent `2251df98b37c4782bab31ccd3a21778ee7bdadba` |
| Upstream base repository/branch | `josch/mmdebstrap` on Muffin Forgejo, `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` observed as repository-page head on 2026-07-31 |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | retained unified patch only; SHA-256 `16d0c6c5e6e26a513fdc7b84ef0bd99a94f60f5e2f30dec83d777169223c67d1` |
| Patch or series | `patches/0001-tarfilter-retain-parent-metadata.patch` |
| Owning issue/PR | Linux Fieldwork #397 unit 21; canonical defect #39; no upstream carrier |
| Latest workflow/run/artifact | local artifact `artifacts/local-matrix.json`, SHA-256 `5f80370c5ce6ec88a2b4fe1c5c111665c1cba6b991f2f8666a394bd8e048e004`; no hosted workflow |

## Current bounded claim

Current mmdebstrap `tarfilter` drops explicit parent directory entries for an exact nested path include because the parent-retention branch derives a glob prefix from translated Python regex text and compares ancestry in one direction. The retained candidate stores the original glob and uses a conservative, component-bounded two-direction relation. The local exact/wildcard/class/boundary matrix preserves parent archive metadata and extraction modes. Full upstream integration remains unexecuted.

## Work completed in this pass

- read issue #397, all issue comments, packet README/index, canonical issue #39, current canonical tarfilter source, current upstream repository state, mirror test carriers, and dpkg reference semantics;
- confirmed unit 21 had no claim, packet, branch, prior code carrier, or equivalent active upstream issue/PR surfaced;
- posted `CLAIMED — unit 21` on #397;
- created `upstream/unit-21-tarfilter-parent-metadata` from `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`;
- reproduced baseline leaf-only output and GNU tar parent modes `0755/0755`;
- selected and documented the original-glob, bounded two-direction predicate;
- built an eight-case local relation matrix and a four-case upstream-style regression;
- retained one source/test/coverage patch and verified synthetic exact-context application, Python compilation, shell syntax, focused candidate execution, cleanup, and rerun;
- completed README, source map, deep dive, tests, decisions, issue draft, PR draft, artifact, script, patch, and this handoff;
- made no external contact.

## Changed paths

- `upstream-packets/units/21-tarfilter-parent-metadata/README.md`
- `upstream-packets/units/21-tarfilter-parent-metadata/SOURCE_MAP.md`
- `upstream-packets/units/21-tarfilter-parent-metadata/DEEP_DIVE.md`
- `upstream-packets/units/21-tarfilter-parent-metadata/TESTS.md`
- `upstream-packets/units/21-tarfilter-parent-metadata/DECISIONS.md`
- `upstream-packets/units/21-tarfilter-parent-metadata/HANDOFF.md`
- `upstream-packets/units/21-tarfilter-parent-metadata/UPSTREAM_ISSUE.md`
- `upstream-packets/units/21-tarfilter-parent-metadata/UPSTREAM_PR.md`
- `upstream-packets/units/21-tarfilter-parent-metadata/scripts/reproduce-parent-metadata.py`
- `upstream-packets/units/21-tarfilter-parent-metadata/artifacts/local-matrix.json`
- `upstream-packets/units/21-tarfilter-parent-metadata/patches/0001-tarfilter-retain-parent-metadata.patch`

## Distinguishing observations

- Replacing `r.pattern` with the original glob alone is insufficient: exact include ancestry still points the opposite way.
- Checking only whether the fixed include prefix descends from the current path is insufficient for `/usr/*/tool`; `/usr/bin` lies below the fixed prefix after a wildcard.
- The selected relation covers both directions and requires a slash boundary, so `/usr2/tool` does not retain `/usr`.
- Leading-wildcard includes retain candidate parents conservatively, consistent with dpkg's documented safety policy.
- Candidate archive entries preserve mode, uid, gid, mtime, and PAX markers because the existing `TarInfo` pass-through remains unchanged once parents survive filtering.
- Canonical `tarfilter` still showed last modification at `87b9b385b38795c58bc13ffb33b8724bed27f7a0`; repository head was `77ec9be5417ee44c96343d2347145585da1b1f94` during review.

## Gates completed

- `python3 -m py_compile scripts/reproduce-parent-metadata.py` — PASS;
- baseline/candidate matrix on Python 3.13.5 and GNU tar 1.35 — PASS;
- eight relation cases — PASS;
- `git apply --check` and `git apply` on exact-context synthetic fixture — PASS;
- patched Python hunk compilation in fixture — PASS;
- `sh -n tests/tarfilter-parent-metadata` from retained patch — PASS;
- focused proposed test against candidate implementation, four cases — PASS;
- cleanup and immediate rerun — PASS.

## Red or neutral runs classified

- Baseline exact include emitted only `usr/bin/tool`; classified as product source behavior.
- Baseline extraction created `usr` and `usr/bin` as `0755`; classified as the downstream consequence of omitted parent members.
- Canonical checkout/application and native coverage gates were unavailable in this environment; classified as an environment/tooling limit, with no result inferred.
- Ordinary last-match-wins leaf matching is unchanged by source review; neutral control only.

## Cleanup state

No processes, sockets, mounts, containers, locks, or temporary extraction directories remain. The packet intentionally retains the script, JSON receipt, patch, and documentation. Local scratch repositories outside the branch carried no live resources and are irrelevant to the durable handoff.

## First incomplete step

Apply the retained patch to an exact checkout of canonical `main@77ec9be5417ee44c96343d2347145585da1b1f94` and inspect any context or formatting difference before creating a candidate commit.

## Next safe action

From an authorized controlled fork or a materialized canonical checkout:

```sh
git checkout -b linux-fieldwork/unit-21-tarfilter-parent-metadata \
  77ec9be5417ee44c96343d2347145585da1b1f94
git apply --check \
  /path/to/linux-fieldwork/upstream-packets/units/21-tarfilter-parent-metadata/patches/0001-tarfilter-retain-parent-metadata.patch
git apply --index \
  /path/to/linux-fieldwork/upstream-packets/units/21-tarfilter-parent-metadata/patches/0001-tarfilter-retain-parent-metadata.patch
./tests/tarfilter-parent-metadata
CMD=./mmdebstrap ./coverage.py tarfilter-parent-metadata
```

Then run the repository formatting/line-length gate, review the complete diff, record the exact candidate head in every packet identity table, and keep external contact disabled.

## Unresolved blockers

- technical: exact canonical patch application and full-source focused execution remain;
- compatibility: maintainer preference for conservative versus tighter glob-prefix viability remains a review question;
- overlap: none surfaced on 2026-07-31; recheck before any authorized submission;
- environment or tooling: no materialized canonical checkout or controlled fork was available here;
- authority: external issue, fork publication, pull request, comment, email, or submission requires explicit authorization.

## Files to read first

1. `README.md`
2. `SOURCE_MAP.md`
3. `DEEP_DIVE.md`
4. `TESTS.md`
5. `DECISIONS.md`
6. issue #39, issue #397, and current canonical tarfilter source

## External-contact state

`false; none occurred`. The only public write was the authorized internal Linux Fieldwork claim/checkpoint routing on issue #397. No upstream issue, pull request, fork publication, comment, review, email, or message was created.

## Do not repeat

- Do not try the original-glob-only substitution; exact includes still lose parents.
- Do not use plain string prefixes without slash boundaries; `/usr` and `/usr2` alias.
- Do not replace the selected conservative predicate with an exact-ancestor-only check without addressing `/usr/*/tool`.
- Do not infer full upstream coverage from the local model or synthetic patch application.
- Do not contact upstream or publish a fork/PR without explicit authorization.
