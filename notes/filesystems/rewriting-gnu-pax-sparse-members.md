# Rewriting GNU PAX sparse members safely

## In simple words

A sparse file has a large logical size but stores only its real data extents. GNU tar can represent that layout with `GNU.sparse.*` PAX metadata plus a compact payload.

A tar rewriter cannot safely copy the expanded logical byte stream while retaining the original sparse metadata. The payload layout and sparse map must describe each other. If one changes without the other, the output archive can be rejected or extract incorrectly.

## What I learned

Python's `tarfile` reader presents a parsed sparse member as its logical file contents. Reading through `extractfile()` can therefore produce zeros for holes and data at logical offsets even when the input archive stored only compact extents.

When writing the member again, there are two valid choices:

1. **Dense output:** remove every `GNU.sparse.*` PAX header, clear the parsed sparse state, keep the logical size, and write the complete logical stream.
2. **Sparse output:** generate a new sparse-map payload and matching PAX metadata from the parsed extent map. Do not reuse input sparse headers after changing the payload layout or member path.

For GNU PAX sparse format 1.0, the stored payload begins with an ASCII extent count and offset/length pairs, padded to a 512-byte tar block, followed by the bytes from each real extent. The PAX headers identify version `1.0`, the member name, and the logical size.

Path transformations matter too. `GNU.sparse.name` must match the final output member name, not the pre-transform name.

Filtering only one required sparse header is not enough to make a valid dense member. The dense fallback must remove **all** `GNU.sparse.*` headers so partial metadata cannot survive.

## Source and provenance

- Project: imported Debian `mmdebstrap`
- Source file: `upstream/mmdebstrap/tarfilter`
- Imported source blob investigated: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Investigation: LF-14 archive extraction and metadata corpus
- Candidate repair: pull request #23

## Example

A useful regression fixture writes three short data extents separated by holes:

```text
offset 0:             BEGIN
offset 1 MiB:         MIDDLE
offset 8 MiB:         END
```

A correct sparse rewrite should preserve:

- the complete extracted SHA-256;
- the three exact extent values;
- zero-filled representative hole bytes;
- the logical size;
- sparse allocation after extraction;
- a compact archive size;
- and a valid archive listing and extraction result.

A dense fallback should preserve the same complete extracted SHA-256 while containing no `GNU.sparse.*` headers.

## Validation

The LF-14 repair regression applies the candidate patch to a temporary copy of the exact imported `tarfilter`, runs the full nine-fixture archive matrix, compares the direct and rewritten sparse file hashes, checks data and hole offsets, and separately filters one required sparse header to force the dense fallback.

The retained negative control runs the unmodified imported source and requires the sparse rewrite to fail. This proves the repair-side test is not only recording output.

## Environment and assumptions

- GNU tar creates and extracts the fixture.
- Python `tarfile` parses the input member and exposes its sparse extent map.
- The candidate normalizes sparse output to GNU PAX sparse format 1.0.
- The current regression runs on the repository's Ubuntu 24.04 CI environment.

## Limits

This note does not claim compatibility with every sparse tar dialect, every Python release, every tar implementation, or malformed adversarial extent maps. Old GNU sparse formats, overlapping or unsorted extents, very large extent counts, and non-seekable parser changes need separate controls.

## Related work

- Related investigation: LF-14 archive extraction and metadata contracts
- Related pull request: #23
- Related issue: #25 covers path and link rewrite metadata interactions
- Source: `upstream/mmdebstrap/tarfilter`
