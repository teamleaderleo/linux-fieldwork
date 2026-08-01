# Handoff — unit 02 caching_proxy complete repair

## State

`ACTIVE`

Exact current-upstream source identity is now verified. The first incomplete step is executing the committed composer and retained matrix against the exact staging snapshot, then publishing the resulting source-only candidate branch.

## Exact stopping point

- Linux Fieldwork repository: `teamleaderleo/linux-fieldwork`
- Linux Fieldwork branch: `upstream/unit-02-caching-proxy-complete-repair`
- Last material packet head before this handoff update: `f5bb95810257bac52c7cac245b2223b9227f31b3`
- Packet: `upstream-packets/units/02-caching-proxy-complete-repair/`
- State: `ACTIVE`
- External contact: unauthorized; none made

## Exact canonical identity

- Project: mmdebstrap
- Canonical repository: `https://gitlab.mister-muffin.de/josch/mmdebstrap`
- Canonical branch: `main`
- Canonical head used by this unit: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Target file: `caching_proxy.py`
- GitHub snapshot branch: `teamleaderleo/mmdebstrap:linux-fieldwork/upstream-main-snapshot`
- Snapshot branch head: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Snapshot target blob: `e57a8516a0c76167894b05fc56be0e3165535488`
- Linux Fieldwork imported target blob: `e57a8516a0c76167894b05fc56be0e3165535488`
- Exact byte equality: `PASS`

## GitHub staging identity

- Repository: `teamleaderleo/mmdebstrap`
- Default branch: `master`
- Default-branch head: `574048f2a720057b75e56622003932f344dc700a`
- Default-branch interpretation: Deepin-style package mirror; do not use as canonical source base
- Controller branch: `linux-fieldwork/unit-02-caching-proxy-complete-repair`
- Controller head: `60ea1c862787473ca362278bb2efb6f5e971b124`
- Controller workflow: `.github/workflows/unit-02-export-and-test.yml`
- Clean source branch: `linux-fieldwork/unit-02-caching-proxy-complete-repair-source`
- Clean source head observed at stop: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Candidate publication state: `NOT OBSERVED`
- Workflow/test result: `UNRESOLVED`; no pass is claimed

## Exact internal candidate identity

- Owning issue: #188
- Canonical composition: merged PR #198
- Final composition head: `5e69cd25e62d0e86364459d97c9df8568ff84187`
- Merge commit: `8d9f7fa92f0cb2f553ca3578b78d7e04f4e4167f`
- Composer: `investigations/caching-proxy-complete-stack/compose_impl.py`
- Composer blob: `00e28cc925ced0c01d9c8e300e7c94515367ca19`
- Atomic input patch blob: `4fe75d312ebb097f1b9d5fa27f9f6e8da61235c1`
- Final exact-head Linux Fieldwork CI: `30580697438` / 612, success
- Predecessor exact-head CI: `30578916643` / 572, success
- Local complete matrix: seven tests, passed twice (`16.425s`, `15.297s`)

## Completed in the latest pass

1. Located the user-controlled GitHub repository `teamleaderleo/mmdebstrap`.
2. Determined that its default `master` branch is a package mirror and is not suitable as the canonical source base.
3. Reviewed peer staging branches for units 05, 06, 07, 09, 10, 13, 14, 15, and 19.
4. Identified `linux-fieldwork/upstream-main-snapshot` as an exact canonical snapshot branch.
5. Verified the exact target blob equality at canonical commit `77ec9be…`.
6. Created the unit-02 controller branch from the exact snapshot.
7. Created the clean unit-02 source branch from the exact snapshot.
8. Added an internal-only export/test workflow to the controller branch.
9. Observed that the clean source branch had not advanced by the stopping point; did not claim a candidate or test success.
10. Recorded peer-branch and staging evidence in `artifacts/github-staging-scan-2026-08-01.md`.
11. Updated the packet README and this handoff.
12. Made no upstream contact and opened no pull request.

## First incomplete step

Determine why the controller workflow did not publish the clean source candidate.

Check the GitHub Actions state for commit:

```text
60ea1c862787473ca362278bb2efb6f5e971b124
```

The expected workflow behavior is:

1. check out `linux-fieldwork/unit-02-caching-proxy-complete-repair-source`;
2. require source commit `77ec9be5417ee44c96343d2347145585da1b1f94`;
3. require source blob `e57a8516a0c76167894b05fc56be0e3165535488`;
4. invoke `investigations/caching-proxy-complete-stack/compose.py` from the Linux Fieldwork unit branch;
5. compile under ordinary and optimized Python;
6. run `tests/test_caching_proxy_complete_stack.py`;
7. commit only `caching_proxy.py` to the clean source branch.

If GitHub Actions is disabled or the workflow failed before producing a useful transcript, run the exporter in a full Linux Fieldwork checkout instead:

```sh
./upstream-packets/units/02-caching-proxy-complete-repair/scripts/export_candidate.sh
cat upstream-packets/units/02-caching-proxy-complete-repair/artifacts/export-receipt.txt
python3 -m unittest -v tests/test_caching_proxy_complete_stack.py
```

## Next safe technical actions

After a candidate is generated:

1. compare it byte for byte with the clean source branch file;
2. retain the candidate digest and patch digest;
3. apply the patch with zero fuzz/offset to canonical commit `77ec9be…`;
4. adapt the seven-case matrix into upstream-native test placement;
5. run ordinary and optimized Python focused tests;
6. verify failed-fill cleanup, retry, concurrency, and post-commit close behavior;
7. immediately rerun the exact candidate after cleanup;
8. review the complete diff against the canonical snapshot;
9. refresh canonical issue/PR overlap immediately before authorization;
10. move to `READY FOR AUTHORIZATION` only when all gates are complete.

## Peer patterns worth retaining

- Unit 05: explicit lifecycle phase for signal/exit precedence.
- Unit 07: validate every cleanup marker before the first mutation.
- Unit 10: parse structured account fields rather than substring matching.
- Unit 13: verify exact base blobs before patch application.
- Unit 14: keep controller machinery separate from the clean candidate branch and retain overlap/test receipts.
- Unit 19: test metadata preservation and round-trip behavior, not only transformed values.

## Required gates still unexecuted

- successful candidate export in the current staging environment;
- clean source-branch publication;
- generated candidate and patch digests;
- zero-fuzz application to current canonical base;
- upstream-native focused test integration;
- ordinary/optimized parity on the published candidate;
- exact-candidate cleanup and immediate rerun;
- final complete-diff review;
- send-date overlap refresh;
- explicit external authorization.

## Known boundaries

- same-UID parent-swap races remain issue #227;
- misses remain uncoalesced;
- publication is pathname-atomic, without crash-durable fsync guarantees;
- checksums/authentication remain outside scope;
- remote deployment policy remains outside scope;
- accepted URI syntax stays intentionally narrow.

## Recovery rule

Use this packet, `artifacts/github-staging-scan-2026-08-01.md`, and the issue #397 unit checkpoint as the source of truth. Do not infer state from chat history.

## Authority

Internal repository work remains authorized. External contact remains unauthorized. No public upstream issue, pull request, merge request, comment, review, email, patch post, or package upload was made.
