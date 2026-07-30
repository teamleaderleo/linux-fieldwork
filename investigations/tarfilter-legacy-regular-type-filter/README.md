# Tarfilter legacy regular-file type filtering

## In simple words

A tar regular file can use type flag `0` or the older NUL flag. Python recognizes both as ordinary files, but `tarfilter --type-exclude=REGTYPE` removes only the `0` form. A local candidate treats both encodings as the same regular-file class so the filter cannot silently retain an ordinary payload.

## Existing work and duplicate search

Searched open Linux Fieldwork issues, pull requests, investigations, tests, notes, and the imported source for `AREGTYPE`, NUL type flags, legacy regular types, and `--type-exclude`. No existing record covered this boundary.

- Canonical issue: #76
- Candidate branch: `fix/tarfilter-legacy-regular-type-filter`
- Candidate patch: `tarfilter-legacy-regular-type-filter.patch`

## Question

Does `--type-exclude=REGTYPE` remove every archive member that the parser classifies as a regular file, including the accepted legacy NUL type flag?

## Source

- Project: imported `mmdebstrap`
- Package/revision: Debian `1.5.7-3`
- Imported file: `upstream/mmdebstrap/tarfilter`
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Source owner: `TypeFilterAction` and `type_filter_should_skip()`
- Import metadata: `upstream/mmdebstrap/.linux-fieldwork-source.json`

## Baseline behavior

`TypeFilterAction` stores only `tarfile.REGTYPE` (`b"0"`) for `REGTYPE` and CLI value `0`. The filter later compares `member.type` by raw equality.

The fixture contains:

- `zero-regular`, type `tarfile.REGTYPE`;
- `nul-regular`, type `tarfile.AREGTYPE` (`b"\0"`);
- one directory control.

Python reports `isfile() == True` for both regular members. The unmodified filter removes `zero-regular` but retains `nul-regular`.

## Candidate

Map `REGTYPE` and `0` to both accepted regular-file flags:

```python
items.extend((tarfile.REGTYPE, tarfile.AREGTYPE))
```

No other type class or archive-writing behavior changes.

## Reproduction

```sh
python3 -m unittest tests.test_tarfilter_legacy_regular_type -v
```

The test applies the retained patch to an exact temporary copy of the imported source.

## Results required

1. The fixture must parse with distinct `REGTYPE`, `AREGTYPE`, and `DIRTYPE` members.
2. The unmodified source must leak only the NUL-type regular member under `--type-exclude=REGTYPE`.
3. The candidate must remove both regular encodings for `REGTYPE` and `0`.
4. The directory control must remain.
5. `--type-exclude=DIRTYPE` must remove only the directory and retain both regular encodings.

## Interpretation

The option is documented as filtering a member type, not one byte spelling of that type. Treating the two accepted regular-file flags as one semantic class matches Python's own `TarInfo.isfile()` classification and prevents regular payloads from bypassing the filter.

## Evidence boundary

- The regression covers Python's `REGTYPE` and `AREGTYPE` constants in an uncompressed USTAR fixture.
- Other vendor-specific or unknown type flags remain outside this change.
- The imported source remains unchanged; the candidate is a retained patch applied in a disposable directory.
- No full upstream mmdebstrap test matrix or other tar implementation is claimed.

## Cleanup and safety

The test uses in-memory archives and `TemporaryDirectory`. It does not extract archive paths, require privilege, mount filesystems, install packages, or accept a caller-controlled deletion root.

## Next step

Keep the local candidate and regression. Recheck exact-head CI and compose the patch with the active tarfilter stacks before any consolidation.

## Authority

Internal Linux Fieldwork work only. No upstream issue, email, merge request, patch submission, comment, or review is authorized or made.
