# GNU sparse tarfilter repair candidate

## Problem

Python's streaming `tarfile` reader exposes a GNU sparse member as its logical expanded byte stream and records the parsed extent map in `TarInfo.sparse`.

The imported `tarfilter` currently writes that logical stream into a new PAX archive while retaining the input `GNU.sparse.*` headers. The output payload and sparse metadata therefore describe different layouts. GNU tar rejects the result with `numeric overflow in sparse archive member`.

## Candidate invariant

Filtering a sparse member must produce one of two valid outcomes:

1. preserve the logical contents and sparse extent layout; or
2. when the caller explicitly filters required sparse metadata, emit valid dense data.

It must never combine expanded logical bytes with stale sparse-map metadata.

## Candidate mechanism

The retained patch normalizes parsed sparse members to GNU PAX sparse format 1.0:

- write a padded sparse-map preamble;
- stream only bytes belonging to parsed data extents;
- set `GNU.sparse.major`, `GNU.sparse.minor`, `GNU.sparse.name`, and `GNU.sparse.realsize` from the final member state;
- use the transformed member path in `GNU.sparse.name`;
- clear Python's in-memory sparse marker before writing the normalized representation.

If a `--pax-exclude` rule removes required sparse headers, the candidate writes the logical stream densely instead.

## Regression control

`tests/test_lf14_sparse_repair.py` applies the retained patch to a temporary copy of the imported source and runs the full nine-fixture LF-14 matrix. It requires:

- zero extraction failures;
- equal sparse logical size;
- retained sparse allocation;
- and an output archive that remains small relative to the logical file.

The existing negative regression remains unchanged and continues to characterize the imported source before the patch is applied.

## Boundary

This is an owned-repository candidate patch against the imported source. It is not an upstream submission and makes no claim about sparse formats not parsed by Python's `tarfile` implementation.
