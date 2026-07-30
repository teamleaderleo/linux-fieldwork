# Update — legacy regular-file type filtering

## Finding

`tarfilter --type-exclude=REGTYPE` maps the semantic regular-file class only to `tarfile.REGTYPE` (`b"0"`). Python also accepts the legacy NUL type flag as `tarfile.AREGTYPE` and reports `TarInfo.isfile() == True`, but the raw equality filter leaves that member in the output.

## Records

- Canonical issue: #76
- Candidate: PR #77
- Investigation: `investigations/tarfilter-legacy-regular-type-filter/README.md`
- Retained patch: `investigations/tarfilter-legacy-regular-type-filter/tarfilter-legacy-regular-type-filter.patch`
- Regression: `tests/test_tarfilter_legacy_regular_type.py`

## Negative control and candidate boundary

The fixture contains `REGTYPE`, `AREGTYPE`, and directory members. The unmodified source must remove the `b"0"` member while leaking the NUL-type member. The candidate maps `REGTYPE` and CLI `0` to both regular-file flags and must remove both without over-filtering the directory or a separate `DIRTYPE` selection.

## Impact

A caller using type exclusion as a content boundary can receive an archive that still contains an ordinary file payload. The issue is medium correctness and requires an accepted legacy tar encoding.

## Authority

Internal Linux Fieldwork record only. No upstream contact.