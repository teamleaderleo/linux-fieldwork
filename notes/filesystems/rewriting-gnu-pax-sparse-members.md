# Rewriting GNU PAX sparse members safely

## In simple words

A sparse file has a large logical size but stores only its real data extents. GNU tar can represent that layout with `GNU.sparse.*` PAX metadata plus a compact payload.

A tar rewriter cannot safely copy the expanded logical byte stream while retaining the original sparse metadata. The payload layout, sparse map, and archive type flag must describe the same representation. If one changes without the others, the output archive can be rejected or extract incorrectly.

## What I learned

Python's `tarfile` reader presents a parsed sparse member as its logical file contents. Reading through `extractfile()` can therefore produce zeros for holes and data at logical offsets even when the input archive stored only compact extents.

When writing the member again, there are two valid choices:

1. **Dense output:** remove every `GNU.sparse.*` PAX header, clear the parsed sparse state, keep the logical size, use a regular-file type flag, and write the complete logical stream.
2. **Sparse output:** generate a new sparse-map payload and matching PAX metadata from the parsed extent map, and emit it as a regular-file member. Do not reuse input sparse headers after changing the payload layout or member path.

For GNU PAX sparse format 1.0, the stored payload begins with an ASCII extent count and offset/length pairs, padded to a 512-byte tar block, followed by the bytes from each real extent. The PAX headers identify version `1.0`, the member name, and the logical size.

The archive type flag is a separate part of the contract. Python preserves `TarInfo.type == GNUTYPE_SPARSE` (`S`) when it parses an old GNU sparse member. Clearing `TarInfo.sparse` does not change that type. A rewriter that converts the member to PAX sparse 1.0 or dense data must explicitly set `TarInfo.type = REGTYPE`; otherwise it emits a hybrid old-GNU/PAX or old-GNU/dense member.

Path transformations matter too. `GNU.sparse.name` must match the final output member name, not the pre-transform name.

Filtering only one required sparse header is not enough to make a valid dense member. The dense fallback must remove **all** `GNU.sparse.*` headers so partial metadata cannot survive.

## Source and provenance

- Project: imported Debian `mmdebstrap`
- Source file: `upstream/mmdebstrap/tarfilter`
- Imported source blob investigated: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Investigation: LF-14 archive extraction and metadata corpus
- Candidate repair: pull request #23
- Type-normalization finding: issue #44

## Example

A useful regression fixture writes three short data extents separated by holes:

```text
offset 0:             BEGIN
offset 1 MiB:         MIDDLE
offset 8 MiB:         END
```

Create the same logical file in two archive dialects:

```sh
tar --format=pax --sparse -cf pax-sparse.tar sparse-source
tar --format=gnu --sparse -cf old-gnu-sparse.tar sparse-source
```

A correct sparse rewrite should preserve:

- the complete extracted SHA-256;
- the three exact extent values;
- zero-filled representative hole bytes;
- the logical size;
- sparse allocation after extraction;
- a compact archive size;
- a regular-file output type;
- and a valid archive listing and extraction result.

A dense fallback should preserve the same complete extracted SHA-256 while containing no `GNU.sparse.*` headers and using a regular-file type.

## Validation

The LF-14 repair regression applies the candidate patch to a temporary copy of the exact imported `tarfilter`, runs the full nine-fixture archive matrix, compares the direct and rewritten PAX sparse file hashes, checks data and hole offsets, and separately filters one required sparse header to force the dense fallback.

The type-normalization extension also generates an old GNU `--format=gnu --sparse` member. Before applying the candidate, it requires that the unmodified rewriter does **not** satisfy the normalized regular-file sparse invariant. After applying the candidate, it requires regular-file type, valid listing and extraction, full content equality, sparse allocation and compact size, plus a regular dense fallback with no sparse headers.

## Environment and assumptions

- GNU tar creates and extracts the fixtures.
- Python `tarfile` parses the input member and exposes its sparse extent map.
- The candidate normalizes parsed sparse output to GNU PAX sparse format 1.0.
- The regression runs on the repository's Ubuntu 24.04 CI environment.

## Limits

This note does not claim compatibility with every sparse tar dialect, every Python release, every tar implementation, or malformed adversarial extent map. The old GNU control covers the GNU tar `--format=gnu --sparse` representation available in current CI; overlapping or unsorted extents, very large extent counts, other historical dialects, and non-seekable parser changes need separate controls.

## Related work

- Related investigation: LF-14 archive extraction and metadata contracts
- Related pull request: #23
- Related issue: #44 tracks old GNU type normalization
- Related issue: #25 covers path and link rewrite metadata interactions
- Source: `upstream/mmdebstrap/tarfilter`
