# GNU sparse tarfilter repair candidate

## Problem

Python's streaming `tarfile` reader exposes a GNU sparse member as its logical expanded byte stream and records the parsed extent map in `TarInfo.sparse`.

The imported `tarfilter` currently writes that logical stream into a new PAX archive while retaining the input `GNU.sparse.*` headers. The output payload and sparse metadata therefore describe different layouts. GNU tar rejects the result with `numeric overflow in sparse archive member`.

A second representation boundary appears with old GNU sparse input. Python preserves the old type flag `GNUTYPE_SPARSE` (`S`) after parsing the extent map. PAX sparse 1.0 and dense output must use a regular-file type flag.

## Candidate invariant

Filtering a parsed sparse member must produce one of two valid outcomes:

1. preserve the logical contents and sparse extent layout in normalized GNU PAX sparse 1.0 form; or
2. when the caller explicitly filters required sparse metadata, emit valid dense regular-file data.

It must never combine expanded logical bytes with stale sparse-map metadata or retain an old GNU type flag after converting the representation.

## Candidate mechanism

The retained patch normalizes parsed sparse members to GNU PAX sparse format 1.0:

- normalize the output member type to `tarfile.REGTYPE`;
- write a padded sparse-map preamble;
- stream only bytes belonging to parsed data extents;
- set `GNU.sparse.major`, `GNU.sparse.minor`, `GNU.sparse.name`, and `GNU.sparse.realsize` from the final member state;
- use the transformed member path in `GNU.sparse.name`;
- clear Python's in-memory sparse marker before writing the normalized representation.

If a `--pax-exclude` rule removes required sparse headers, the candidate removes all sparse headers, keeps the regular-file type, and writes the logical stream densely instead.

## Regression control

`tests/test_lf14_sparse_repair.py` applies the retained patch to a temporary copy of the imported source and runs the full nine-fixture LF-14 matrix. It requires:

- zero extraction failures;
- equal sparse logical size and contents;
- retained sparse allocation;
- an output archive that remains small relative to the logical file;
- valid dense fallback when required sparse metadata is filtered;
- and regular-file output type for both sparse and dense representations.

The extension for issue #44 generates an old GNU archive with `tar --format=gnu --sparse`. Before applying the candidate it requires that the unmodified rewriter does not satisfy the normalized regular-file sparse invariant. After applying the candidate it requires valid listing, extraction, content equality, sparse allocation, compact archive size, regular-file type, and a regular dense fallback with no `GNU.sparse.*` headers.

## Boundary

This is an owned-repository candidate patch against the imported source. It is not an upstream submission. The old GNU control covers the dialect emitted by current GNU tar with `--format=gnu --sparse`; other historical sparse representations and malformed extent maps remain separate work.
