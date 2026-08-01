# GitHub staging scan — 2026-08-01

## Repository identity

- Accessible staging repository: `teamleaderleo/mmdebstrap`
- Default branch: `master`
- `master` head: `574048f2a720057b75e56622003932f344dc700a` (`feat: update mmdebstrap to 1.5.7-3`)
- Interpretation: this is a Deepin-style package mirror, not a byte-for-byte fork whose default branch tracks canonical `josch/mmdebstrap`.
- Exact canonical snapshot branch: `linux-fieldwork/upstream-main-snapshot`
- Snapshot head: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Snapshot `caching_proxy.py` blob: `e57a8516a0c76167894b05fc56be0e3165535488`
- Unit 02 imported source blob: `e57a8516a0c76167894b05fc56be0e3165535488`
- Result: exact byte identity is verified; the former first gate is complete.

## Existing worker branches reviewed

| Branch | Observed head | Useful change or pattern |
| --- | --- | --- |
| `linux-fieldwork/unit-05-run-qemu-result-precedence` | `6efe6945f9f89cff57fe84086ede7bda747c3879` | Adds an explicit cleanup phase and closes INT/TERM trap setup windows in `run_qemu.sh`. |
| `linux-fieldwork/unit-06-chrootless-maintainer-boundary` | `574048f2a720057b75e56622003932f344dc700a` | Still points at package-mirror `master`; no isolated candidate observed. |
| `linux-fieldwork/unit-07-file-mirror-confinement` | `8b8dce6910badeda1e72e28f471fa220a22eea7d` | Canonicalizes the generated root and preflights every cleanup-marker entry before mutation. |
| `linux-fieldwork/unit-09-dev-ptmx-bsdutils` | `43082a6bc959e2d7cefae48f52e045cc90869287` | Adds `bsdutils` to the `dev-ptmx` test dependency set. |
| `linux-fieldwork/unit-10-subid-exact-match` | `eb75165459760cd4b9d8801147393bbde0535df6` | Matches only field 1 of `/etc/subuid` and `/etc/subgid`, avoiding substring false positives. |
| `linux-fieldwork/unit-13-make-mirror-top-level-lifecycle` | `9c55456bb39290345b9f10934ddf3dd2a94a220b` | Uses a controller workflow to verify exact base blobs, apply a retained patch, and run focused regressions. |
| `linux-fieldwork/unit-14-make-mirror-update-cache` | `76a7a49f6439797ae1e84fec2031d78969ba74ae` | Separates controller, source, and upstream-main candidate branches and retains native/overlap receipts. |
| `linux-fieldwork/unit-15-tarfilter-transform-metadata` | `505bf81079a3b76c7d56bffa8097c1b5a494898e` | Registers a focused tarfilter metadata regression in `coverage.txt`. |
| `linux-fieldwork/unit-19-tarfilter-pax-idshift` | `07e89c68dbed198b04bb60aeb1947433f6ead0b0` | Adds PAX uid/gid shift and round-trip coverage while preserving unrelated PAX metadata. |

## Unit 02 staging created

- Controller branch: `linux-fieldwork/unit-02-caching-proxy-complete-repair`
- Controller base: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Controller workflow commit: `60ea1c862787473ca362278bb2efb6f5e971b124`
- Clean source branch: `linux-fieldwork/unit-02-caching-proxy-complete-repair-source`
- Clean source branch current head: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Workflow intent: verify the exact base/blob, invoke the committed composer, compile under ordinary and optimized Python, run the retained seven-test matrix, and publish only `caching_proxy.py` to the clean source branch.
- Observed result during this session: the clean source branch did not advance. No candidate/test success is claimed. GitHub Actions execution or repository Actions policy remains the first unresolved staging gate.

## Decisions

1. Use `linux-fieldwork/upstream-main-snapshot`, not package-mirror `master`, as the source base.
2. Treat `teamleaderleo/mmdebstrap` as an internal staging repository only. It is not the canonical delivery destination.
3. Keep controller machinery off the clean candidate source branch.
4. Do not open a GitHub pull request; canonical delivery remains Forgejo and still requires explicit external authorization.
5. Reuse the strongest worker pattern: exact base identity, isolated clean source branch, focused tests, and durable receipts.

## External-contact state

No upstream issue, pull request, comment, review, email, or patch submission was made.
