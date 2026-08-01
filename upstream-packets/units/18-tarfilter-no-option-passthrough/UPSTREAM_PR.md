# Upstream pull-request draft

## Title

tarfilter: restore byte-preserving no-option passthrough

## Summary

`tarfilter` now copies stdin to stdout byte-for-byte when every modifying option is inactive.

The previous guard tested whether `strip_components` existed. `argparse` always creates that attribute, with `None` when omitted, so the copy path could never run. No-option invocations consequently parsed and re-emitted archives as uncompressed PAX.

The predicate now:

- checks strip-components and ID shift by value;
- treats explicit numeric zero as no-operation, consistent with the existing source behavior;
- includes transforms;
- retains the custom-action presence checks for path, PAX, and type filters.

## Tests

The focused regression:

- proves the unmodified source rewrites gzip input and removes its gzip signature;
- requires byte identity for plain, gzip, bzip2, xz, and GNU PAX sparse archives;
- requires byte identity for `--strip-components=0` and `--idshift=0`;
- verifies active path, PAX, type, strip, transform, and ID-shift operations enter the rewrite path and produce the expected result.

The patch applies to current `tarfilter` with `patch --fuzz=0` and the candidate compiles with Python.

## Scope

This change only restores the existing no-operation copy path. It does not alter archive rewriting semantics when any modifying option is active.

## Contact state

Draft only. External submission requires explicit authorization.
