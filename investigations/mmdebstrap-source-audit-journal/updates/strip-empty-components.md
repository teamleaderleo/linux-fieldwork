# Update — strip-components and repeated separators

## Finding

`tarfilter` implements `--strip-components` with `member.name.split('/')`. Repeated separators create empty fields that consume the requested count, while GNU tar counts nonempty pathname components.

Examples:

- `a//b/file`, count `2`: GNU tar `file`; imported source `b/file`.
- `a///file`, count `2`: GNU tar extracts nothing; imported source emits `/file`.

## Records

- Canonical issue: #81
- Candidate: PR #83
- Validated head: `49a811e548967974b715a1a3664d5650774b8645`
- Exact-head CI: run `30538411969`, success
- Investigation: `investigations/tarfilter-strip-empty-components/README.md`
- Retained patch: `investigations/tarfilter-strip-empty-components/tarfilter-strip-empty-components.patch`
- Regression: `tests/test_tarfilter_strip_empty_components.py`

## Candidate boundary

The candidate scans nonempty components and preserves the original substring after the separator following the last removed component. It matches GNU tar for repeated-separator, `./`-prefixed, and ordinary controls and omits the insufficient-component case.

Traversal sanitization, trailing-directory dialects, and automatic integration into hard-link targets remain outside this focused patch. Consolidation with #25 should reuse the same scanner for `linkname` and regenerate PAX reference metadata.

## Authority

Internal Linux Fieldwork record only. No upstream contact.