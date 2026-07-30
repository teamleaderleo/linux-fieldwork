# LF-14 — Archive Extraction and Metadata Contracts

## In simple words

Root filesystem archives describe paths, links, ownership, permissions, and special metadata. This lane builds a reusable archive corpus and tests whether extraction stays inside the target while preserving every supported property.

## Programme

[`Filesystems, archives, and disk images`](../../STATUS.md)

## State

`active` — the `mmdebstrap` autopkgtest investigation has produced the first archive-manifest and comparison tools while the full extraction matrix remains open.

## Active work

- [`mmdebstrap` autopkgtest failure 1141078](../../../../investigations/mmdebstrap-autopkgtest-1141078/README.md) records root archive ownership, modes, links, device metadata, PAX extras, timestamps, content hashes, and member order before extraction.

## Question

How do bootstrap and image tools handle traversal paths, symlink races, hard links, sparse files, xattrs, ACLs, capabilities, device nodes, and numeric ownership?

## Why this could matter

Extraction errors can escape a target, lose security metadata, change file relationships, or create a root filesystem whose runtime behavior differs from its source archive.

## Likely targets

`mmdebstrap` tar filters, GNU tar, `libarchive`, `dpkg-deb`, and container-image unpackers.

## First probe

Create one canonical archive case per feature and extract under ordinary, rootless, privileged, and restricted target-directory conditions where available. Compare path containment and metadata round-trip.

## Environment

Current CI for ordinary links, paths, sparse files, and numeric ownership. Privileged CI for device nodes, capabilities, ACLs, and selected xattrs.

## Promotion signal

Promote when extraction escapes the target, follows an unsafe link, drops required metadata silently, or behaves inconsistently across documented modes.

## Stop signal

Close when unsupported features fail precisely and supported metadata survives the declared round-trip.

## Expected outputs

- reusable archive corpus;
- extraction matrix;
- metadata comparison tool or script;
- candidate investigation or retained compatibility map.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.
