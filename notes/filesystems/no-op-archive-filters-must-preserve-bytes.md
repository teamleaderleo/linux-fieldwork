# No-op archive filters must preserve bytes

## In simple words

An archive filter invoked with no active filtering or rewrite option should not parse and recreate the archive. A true no-op should copy the input bytes unchanged.

Re-serialization can silently change compression, archive format, header layout, metadata encoding, sparse maps, and checksums even when extracted files look the same.

## What I learned

Command-line parsers often create attributes for omitted options. A fast-path predicate must check whether an operation is active, not merely whether an attribute exists.

For `argparse`, a normal optional argument such as `--strip-components` exists with value `None` when absent. Custom actions may create attributes only when used. The no-op predicate must account for both styles and must include every modifying operation.

Explicit numeric zero can be treated as no-op only when the normal implementation also treats zero as no change. Tests should prove that real transform and ID-shift options still bypass the copy path.

Compression is part of the byte contract. A gzip, bzip2, or xz tar stream parsed and emitted as an uncompressed PAX archive is not a pass-through even if extraction succeeds.

## Source and provenance

- Project: imported `mmdebstrap`
- File: `upstream/mmdebstrap/tarfilter`
- Canonical issue: #29
- Candidate pull request: the `fix/tarfilter-no-option-passthrough` branch

## Validation

The retained regression compares complete input and output bytes for:

- uncompressed PAX tar;
- gzip-compressed tar;
- bzip2-compressed tar;
- xz-compressed tar;
- GNU PAX sparse tar.

The negative control proves the unmodified source changes gzip input and emits a non-gzip stream. Separate controls prove active transform and ID-shift options still modify the archive.

## Limits

Byte-preserving passthrough does not validate the input archive or guarantee it is safe to extract. It only preserves the caller's stream when no operation was requested.

## Related work

- Issue #29
- Issue #27, closed as a duplicate
- LF-14 sparse rewrite candidate PR #23
- Investigation: `investigations/tarfilter-no-option-passthrough/`
