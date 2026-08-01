# Upstream pull request draft

Status: `DRAFT`  
Proposed destination: canonical mmdebstrap repository  
Proposed base branch: repository default branch at current canonical head  
Controlled review branch: `teamleaderleo/mmdebstrap:linux-fieldwork/unit-19-tarfilter-pax-idshift`  
Controlled review head: `07e89c68dbed198b04bb60aeb1947433f6ead0b0`  
Canonical-lineage candidate: `NEEDS REBASE`  
External contact authorized: `false`

## Proposed title

`tarfilter: regenerate shifted PAX uid and gid`

## Draft

### Summary

This change keeps `tarfilter --idshift` effective for members whose numeric ownership requires PAX extended headers.

The filter already increments `TarInfo.uid` and `TarInfo.gid`. Existing PAX `uid` and `gid` strings remained attached to the member and overrode those new values during output serialization. Large-ID members therefore read back with their original ownership while ordinary header-sized members shifted correctly.

After a valid shift, the filter removes only the stale numeric PAX keys. Python regenerates them from the shifted fields when PAX encoding is required.

### Before

A member with uid `1000000000` and gid `1000000001` processed with `--idshift=7` reads back as `1000000000:1000000001`. An ordinary `1000:1001` control reads back as `1007:1008`.

### After

The large member reads back as `1000000007:1000000008`, with matching regenerated PAX strings. The ordinary control continues to read back as `1007:1008` without unnecessary numeric PAX keys. Applying `--idshift=-7` restores the original ownership.

### Implementation

The id-shift block removes `member.pax_headers["uid"]` and `["gid"]` after negative-result validation and integer mutation. Other PAX keys remain attached to the member. The existing native id-shift test gains a forced-large-ID member alongside the ordinary control.

### Controlled materialization

The change is materialized for review in `teamleaderleo/mmdebstrap`:

- mirror base: `master` at `574048f2a720057b75e56622003932f344dc700a`;
- branch: `linux-fieldwork/unit-19-tarfilter-pax-idshift`;
- source commit: `1cd61501e18b5ffd861eceac9b70b1284fb0a0b6`;
- branch head: `07e89c68dbed198b04bb60aeb1947433f6ead0b0`;
- changed paths: only `tarfilter` and `tests/tarfilter-idshift`;
- compare state: ahead by two, behind by zero;
- attached statuses: none observed.

This GitHub repository is a package-source mirror with a different commit lineage from canonical Forgejo. Its two target base blobs exactly match the packet/import blobs, so it is suitable for review and test execution. It is not yet the exact canonical-lineage submission branch.

### Tests

Completed internal evidence:

- exact imported-source regression on the two-line candidate, including a losing baseline, ordinary control, regenerated-key assertions, payload preservation, and negative-shift round trip;
- Linux Fieldwork CI run `30538012863` passed on exact prior candidate head `8d6443626e4338b180ec0533969bfe4d32b20d52`;
- fresh Python 3.13.5 semantic regression passed twice with identical output and preserved unrelated PAX comments;
- the native detector exits `1` with `large ownership was not shifted` on the current model and exits `0` on the candidate model;
- controlled branch contents and exact two-file fence were verified.

Required exact-head receipts before submission:

```sh
black --check ./tarfilter
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
```

The named test is declared `Needs-QEMU: true`. The project runner checks the generated test with ShellCheck and shfmt. Debian's package autopkgtest uses `HAVE_QEMU=no`, so its green result alone does not execute this named test.

### Compatibility

The change affects active nonzero numeric ID shifting when retained PAX `uid` or `gid` values conflict with the shifted fields. Paths, links, payloads, modes, timestamps, user/group names, and unrelated PAX metadata remain unchanged. Ordinary numeric IDs continue to use the base tar header when representable.

### Related issue

A separate upstream issue is unnecessary unless the project requests one.

## Proposed commit

`tarfilter: regenerate shifted PAX uid and gid` — source correction and native regression in one commit.

The controlled review branch currently uses two commits for traceability; squash or rebuild as one commit on the canonical lineage before submission.

## Reviewer notes

Removing the two stale numeric keys instead of assigning replacement strings preserves Python's representation choice: ordinary values remain in ordinary headers, while large values receive regenerated PAX records. Clearing the complete PAX dictionary would discard unrelated metadata and is intentionally avoided.

The test requires the project's QEMU-backed path. A package autopkgtest configured with `HAVE_QEMU=no` skips `tarfilter-idshift` and cannot serve as the focused receipt.

## Submission checklist

- [x] Controlled writable repository exists.
- [x] Controlled review branch exists at `07e89c68dbed198b04bb60aeb1947433f6ead0b0`.
- [x] Controlled branch changes only `tarfilter` and `tests/tarfilter-idshift`.
- [x] Both controlled base target blobs exactly match the packet/import blobs.
- [ ] Candidate rebuilt or rebased onto canonical head `77ec9be5417ee44c96343d2347145585da1b1f94` or its reviewed successor.
- [ ] Complete canonical-lineage diff reviewed.
- [ ] Baseline regression fails and candidate passes in complete native test style.
- [ ] `black --check ./tarfilter` passes.
- [ ] Generated native test passes project ShellCheck and shfmt settings.
- [ ] QEMU-backed `CMD=./mmdebstrap ./coverage.sh tarfilter-idshift` passes twice on the exact candidate head.
- [ ] Project-required ordinary gates pass.
- [x] Active indexed equivalent work checked on 2026-08-01.
- [x] Draft contains no Linux Fieldwork-only routing in the proposed submitted body.
- [ ] Explicit authorization recorded.
- [ ] Public canonical PR and exact submitted head recorded after submission.