# Deep dive

## Question and observed failure

Does `tarfilter --idshift=N` preserve the requested shifted uid/gid when an input member carries numeric ownership in PAX extended headers?

The answer on the current source is no. For a member with uid `1000000000` and gid `1000000001`, `--idshift=7` changes the in-memory `TarInfo` fields to `1000000007` and `1000000008`, then writes the retained input PAX strings. Reading the output yields the original large IDs. An ordinary member with uid `1000` and gid `1001` shifts to `1007` and `1008`, so a header-sized-only test misses the defect.

This result belongs to `tarfilter`'s metadata mutation path. The fixture uses Python's own PAX writer and reader, the command reports success, and the ordinary control proves the shift path executes.

## Source mechanism

The relevant order in `tarfilter` is:

1. read a `TarInfo` member, including `member.pax_headers`;
2. filter requested PAX keys;
3. validate that a negative shift cannot produce a negative uid or gid;
4. add the shift to `member.uid` and `member.gid`;
5. pass the member to `tarfile.addfile()`.

For large numeric values, Python records PAX `uid` and `gid` strings. Existing `TarInfo.pax_headers` participate in output formatting and remain authoritative when the archive is parsed again. Changing only the integer fields leaves contradictory metadata in one object.

The selected correction runs after successful validation and numeric mutation:

```python
member.uid += args.idshift
member.gid += args.idshift
member.pax_headers.pop("uid", None)
member.pax_headers.pop("gid", None)
```

The writer then chooses ordinary tar numeric fields or regenerated PAX keys from the new values.

## Reproduction narrative

The distinguishing fixture contains two regular files:

- `large`: uid `1000000000`, gid `1000000001`, forcing PAX numeric keys;
- `small`: uid `1000`, gid `1001`, fitting ordinary numeric header fields.

Both also carry an unrelated PAX `comment` and a small payload. The baseline transformation shifts the two integer fields while retaining every PAX key. The large member reads back unchanged; the ordinary member reads back shifted. The candidate removes only stale numeric keys, after which both read back shifted, the large member carries regenerated string values, unrelated comments remain, and `-7` restores original ownership and payloads.

Full commands and receipts are in `TESTS.md`.

## Approach history

### Approach A — update PAX uid/gid strings directly

- Mechanism: compute `str(member.uid)` and `str(member.gid)` after shifting and assign both keys.
- Evidence: this would make large IDs coherent.
- Result: rejected.
- Compatibility cost: it would add PAX numeric keys to ordinary members that currently fit the base header, changing archive representation beyond the required correction.

### Approach B — rebuild or clear all PAX metadata

- Mechanism: discard the complete PAX dictionary and let Python regenerate metadata.
- Evidence: numeric ownership would become coherent.
- Result: rejected.
- Compatibility cost: xattrs, comments, timestamps, sparse metadata, and other retained headers could disappear. That scope overlaps the broader metadata unit.

### Approach C — remove only stale numeric ownership keys

- Mechanism: pop `uid` and `gid` after validated shifting.
- Evidence: prior exact-source regression, accepted review, successful CI, and fresh semantic probe.
- Result: selected.
- Compatibility cost: output representation changes only where the old numeric PAX values contradicted the requested shift.

### Approach D — treat the existing ordinary id-shift test as sufficient

- Mechanism: rely on header-sized IDs.
- Evidence: ordinary IDs shift correctly on both baseline and candidate.
- Result: rejected as a detector.
- Compatibility cost: none, but it cannot observe PAX authority and produces a false sense of coverage.

### Approach E — retain the original Linux Fieldwork unified patch unchanged

- Mechanism: reuse the patch whose path is `upstream/mmdebstrap/tarfilter`.
- Evidence: PR #78 final revision applied and passed.
- Result: superseded for upstream packaging.
- Compatibility cost: its repository path is Linux Fieldwork-specific. The packet retains a clean upstream-root `tarfilter` hunk.

## Selected correction

Remove only `member.pax_headers["uid"]` and `["gid"]` after the shift passes negative-value validation and updates the numeric fields. Add a forced-large-ID case to the existing upstream-native `tests/tarfilter-idshift` test. This is the smallest coherent correction because the defect and detector share one option, one source block, and one existing native test owner.

## Why the changes belong together

The source hunk and regression assert one invariant: the serialized archive's numeric identity equals the validated shifted `TarInfo` identity for both base-header and PAX representations. Splitting the test from the source would leave either an unreviewed behavior change or a permanently failing detector.

## Compatibility analysis

### Bytes and logical content

Archive bytes can change because regenerated PAX records contain shifted values. File payload bytes remain unchanged. Ordinary IDs continue to use the base tar header when representable.

### Ownership and metadata

Numeric uid/gid change exactly by the requested shift. Existing user/group names remain unchanged. Unrelated PAX keys remain present. The correction does not alter modes, timestamps, paths, link targets, device numbers, or type flags.

### Error and continuation

Negative-result validation still executes before key removal. A rejected shift exits through the existing error path. A valid member continues through transforms and output with the same ordering.

### Supported runtime

The retained probe passed on Python 3.13.5. PR #78 tested the exact imported source under the repository CI environment. The current upstream source remains the same tarfilter file revision, while a clean current-head checkout test remains pending.

### Option interactions

PAX include/exclude filtering runs before id shifting. A valid nonzero shift makes numeric ownership derived from shifted fields even when an input filter retained the old keys. A filter that removed them already sees the same final state. Zero shift leaves the block untouched. Path, type, transform, and strip semantics remain outside this patch.

## Negative controls and losing mutations

- Keeping PAX `uid`/`gid` while changing integer fields loses: the large member reads back with original ownership.
- The ordinary member shifts on the baseline, proving the command and detector are active.
- Removing only one numeric key would leave one identity dimension stale; the proposed upstream test should assert uid and gid independently.
- Replacing both keys with old strings loses identically to the baseline.
- The inverse-shift round trip detects a candidate that merely hard-codes the positive result.
- Unrelated PAX comments detect overbroad metadata clearing.

## Current upstream and historical review

- Issue #37 documented the defect and exact source owner.
- PR #78 produced the accepted two-line correction and a focused exact-source Python regression.
- Exact-head review at `8d6443626e4338b180ec0533969bfe4d32b20d52` found no blocker.
- Linux Fieldwork CI run `30538012863` passed.
- On 2026-08-01 the canonical repository head was observed at `77ec9be5417ee44c96343d2347145585da1b1f94`; the tarfilter file still ended at commit `87b9b385b38795c58bc13ffb33b8724bed27f7a0` and retained the uncorrected block.
- Indexed issue/PR searches found no equivalent active correction. This is an overlap search result, not proof about unindexed private or draft work.

## Remaining questions

1. **Native test integration:** inspect the exact current `tests/tarfilter-idshift` shell test and add the large-ID case in its established style. Discriminator: focused test fails on exact base and passes on candidate.
2. **Current-head application:** obtain a current upstream checkout at `77ec9be5417ee44c96343d2347145585da1b1f94`. Discriminator: `git am` or equivalent applies with zero fuzz/offset and complete diff contains only source plus native test.
3. **Ordinary gate:** run the project-declared focused test entry point and any formatting gate. Discriminator: exact candidate head passes and immediate rerun remains clean.
4. **Delivery identity:** verify or create a controlled fork. Discriminator: exact fork, branch, and compare URL are recorded before authorization review.

## Evidence boundary

Demonstrated: Python tarfile PAX serialization semantics, exact prior imported-source behavior, current public source persistence, ordinary/large ID distinction, unrelated PAX and payload preservation, and inverse shift.

Pending: full current repository checkout, native shell-test integration, project-wide test orchestration, alternate Python releases, and external tar reader matrix. The patch performs no extraction, privilege change, mount, package install, network mutation, or external publication.

## Reopen triggers

- upstream changes the id-shift block or takes ownership of numeric PAX regeneration elsewhere;
- Python tarfile changes how caller-supplied PAX `uid`/`gid` interact with `TarInfo` fields;
- an active upstream equivalent appears;
- native testing shows a representation compatibility requirement that conflicts with key removal;
- unit 15 adopts the same exact numeric ownership correction and provides a stronger integrated candidate.
