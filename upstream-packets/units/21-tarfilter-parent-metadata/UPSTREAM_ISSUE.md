# Upstream issue draft

Status: `DRAFT`  
Proposed destination: mmdebstrap Forgejo issue tracker, only if maintainers prefer an issue before a pull request  
External contact authorized: `false`

## Proposed title

tarfilter drops parent directory metadata for nested path includes

## Draft

### Summary

`tarfilter` can omit explicit directory or symlink parents when an exclude rule is followed by a nested path include. Extraction then recreates missing directories with default metadata.

### Observed behavior

An input archive contains:

```text
usr/          mode 0700
usr/bin/      mode 0711
usr/bin/tool  mode 0755
```

Filtering it with:

```sh
./tarfilter --path-exclude='/*' --path-include='/usr/bin/tool' \
  < input.tar > output.tar
```

produces an archive containing only `usr/bin/tool`. GNU tar creates `usr/` and `usr/bin/` during extraction as mode `0755`, and the explicit parent uid, gid, mtime, and PAX metadata are absent from the filtered archive.

### Expected behavior

A nested include retains explicit directory and symlink parents that can lead to an included member, preserving their archive metadata.

### Minimal reproduction

The proposed regression creates a PAX archive in Python, runs the command above, and asserts that the output contains `usr`, `usr/bin`, and `usr/bin/tool` with the original parent metadata.

### Source analysis

`PathFilterAction` stores only a compiled `fnmatch.translate()` regex. The parent-retention branch then applies a shell-glob prefix expression to that translated regex text. It also tests ancestry in a direction that cannot retain parents for an exact include.

### Evidence

Reproduced on Python 3.13.5 and GNU tar 1.35. A candidate that retains the original glob and applies component-bounded ancestry in both directions passes exact, wildcard, character-class, and `/usr` versus `/usr2` boundary cases.

### Compatibility and scope

Ordinary last-match-wins path filtering stays unchanged. The parent special case remains conservative and may retain extra directories after an early wildcard, consistent with dpkg's documented behavior. PAX filtering, type filtering, transforms, id shifting, and path normalization remain unchanged.

### Proposed direction

Retain the original path glob beside the compiled matcher. Derive the literal prefix from the glob text and use component-bounded ancestry in both directions when deciding whether an excluded directory or symlink can lead to an included descendant.

## Submission checklist

- [ ] Current public issue and pull-request overlap rechecked.
- [x] Affected current upstream revision confirmed through repository/source review.
- [x] Reproduction is minimal and safe.
- [x] No private credentials, internal-only links, or unsafe artifacts included.
- [x] Exact external destination confirmed.
- [ ] Explicit authorization recorded.
- [ ] Submitted public reference and timestamp recorded in the unit `README.md` and `DECISIONS.md`.
