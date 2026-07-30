# Tarfilter PAX ownership id shifting

## In simple words

`tarfilter --idshift` changes the numeric UID and GID stored on a parsed member, but an existing PAX `uid` or `gid` header can override those new values when the archive is written and read again. Large ownership values therefore appear to shift successfully inside the process while the output archive still carries the original ownership. The local candidate removes stale numeric PAX keys after shifting so Python regenerates them from the new values.

## Existing work and duplicate search

- Canonical issue: #37
- Existing upstream-style test: `upstream/mmdebstrap/tests/tarfilter-idshift`
- No open or closed Linux Fieldwork pull request was found for the PAX numeric-header boundary.
- Candidate branch: `fix/tarfilter-pax-idshift`
- Candidate patch: `tarfilter-pax-idshift.patch`

The upstream-style test covers ordinary header-sized IDs and round-trip shifting but does not force PAX `uid`/`gid` records.

## Question

Does `--idshift` produce the requested ownership in the output archive when the input member's numeric IDs require PAX headers?

## Source

- Project: imported `mmdebstrap`
- Package/revision: Debian `1.5.7-3`
- Imported file: `upstream/mmdebstrap/tarfilter`
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Source owner: the PAX-header filter and `args.idshift` block in `main()`
- Import metadata: `upstream/mmdebstrap/.linux-fieldwork-source.json`

## Baseline behavior

The source first retains PAX headers, then shifts `member.uid` and `member.gid`:

```python
member.uid += args.idshift
member.gid += args.idshift
```

Python's PAX writer starts from the existing `member.pax_headers`. If those headers contain `uid` and `gid`, the stale strings override the changed base fields when the output is parsed.

The regression uses:

- one member with UID `1000000000` and GID `1000000001`, forcing PAX numeric headers;
- one ordinary member with UID `1000` and GID `1001` as a control;
- shift value `+7`.

The unmodified filter shifts the ordinary member but the large member still reads with its original IDs.

## Candidate

After validating and applying the numeric shift, remove the stale numeric PAX keys:

```python
member.pax_headers.pop("uid", None)
member.pax_headers.pop("gid", None)
```

When the new values still require PAX representation, Python regenerates `uid` and `gid` from the shifted fields. Header-sized values continue to use the ordinary tar header.

## Reproduction

```sh
python3 -m unittest tests.test_tarfilter_pax_idshift -v
```

The test applies the retained patch to an exact temporary copy of the imported source.

## Results required

1. The large fixture member must carry source PAX `uid` and `gid` keys.
2. The ordinary member must not require those keys.
3. The unmodified source must leave the large IDs unchanged after `+7` while shifting the ordinary control.
4. The candidate must shift both members.
5. Regenerated large-member PAX keys must contain the shifted values.
6. File payloads must remain equal.
7. Applying `-7` to the candidate output must restore the original numeric ownership and payloads.

## Interpretation

PAX numeric ownership is authoritative archive metadata, not optional decoration. A correct shift must either update those keys or remove them so the writer regenerates consistent metadata. Clearing only `uid` and `gid` is narrower than rebuilding unrelated PAX headers and composes with the existing xattr behavior.

## Evidence boundary

- The regression uses Python's PAX writer and reader and IDs that exceed the ordinary header range.
- User and group names are intentionally unchanged; the option documents a numeric shift.
- Interaction with explicit `--pax-exclude=uid` or `gid` and every external tar implementation remains outside this focused change.
- The imported source remains unchanged; the candidate is applied in a disposable directory.

## Cleanup and safety

The test uses in-memory archives and `TemporaryDirectory`. It does not extract files, require privilege, install packages, mount filesystems, or delete a caller-controlled root.

## Next step

Keep the candidate and regression, verify exact-head CI, and compose it with the other tarfilter metadata patches before consolidation.

## Authority

Internal Linux Fieldwork work only. No upstream issue, email, merge request, patch submission, comment, or review is authorized or made.
