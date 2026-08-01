# Upstream issue draft

Status: `NOT NEEDED`  
Proposed destination: `josch/mmdebstrap` Forgejo issue tracker only if maintainers require an issue  
External contact authorized: `false`

A standalone issue is currently unnecessary because the defect, candidate, and regression can be described directly in a pull request. Keep this file as the fallback draft.

## Proposed title

`tarfilter: keep transformed paths, link targets, and PAX metadata consistent`

## Draft

### Summary

`tarfilter --transform` advertises GNU tar-style substitution, but the current implementation uses Python's default global replacement, accepts only a narrow flag form, changes member names without selected link targets, and can preserve stale PAX path metadata. `--strip-components` similarly leaves hard-link targets and long PAX fields inconsistent.

### Observed behavior

For a member named `a/a`, `--transform='s/a/b/'` produces `b/b`, while GNU tar produces `b/a`. Explicit `g` and numeric occurrence flags are rejected.

For `prefix/target`, a hard link to that member, and a symlink whose target text is `prefix/target`, a default transform removes the prefix from member names while retaining prefixed link targets. Long PAX `path` and `linkpath` values can override a requested strip or rename.

### Expected behavior

The supported transform subset follows GNU tar for first/global replacement, case-insensitive matching, whole-match replacement, numeric occurrence selection, and target scopes. Selected member and link fields stay consistent, and stale PAX names no longer override corrected values.

### Minimal reproduction

```text
Create a PAX archive with member a/a.
Run: tarfilter --transform='s/a/b/'
Observed name: b/b
GNU tar name: b/a

Create prefix/target plus hard and symbolic links to prefix/target.
Run: tarfilter --transform='s,^prefix/,,'
Observed: link targets still contain prefix/
GNU tar default: member, hard-link target, and symlink target are transformed.
```

### Source analysis

`TransformAction` stores a compiled Python regex and replacement string. The archive loop calls `re.sub()` without a replacement count and only on `member.name`. Strip also changes only `member.name`. Existing `pax_headers` are copied unless filtered by user options.

### Evidence

A focused differential matrix against GNU tar 1.35 covers ordinary/global replacement, case-insensitive matching, whole-match `&`, escaped delimiters, default and uppercase-`S` target scopes, hard-link extraction and inode identity, long PAX path/linkpath regeneration, numeric selectors, zero, repeated decimal runs, and non-ASCII selector rejection.

### Compatibility and scope

The candidate preserves the current Python pattern dialect. GNU basic/extended regex translation, expression lists, persistent flags, case conversion, locale/collation, and other transform grammar remain separate work.

### Proposed direction

Parse the supported substitution state explicitly, apply it to selected member and link fields, and remove stale `path` or `linkpath` fields whenever their logical values change.

## Submission checklist

- [x] Current public issue and pull-request overlap rechecked on 2026-08-01.
- [x] Affected current upstream revision confirmed.
- [x] Reproduction is minimal and safe.
- [x] No private credentials or unsafe artifacts included.
- [ ] Exact external destination reconfirmed immediately before submission.
- [ ] Explicit authorization recorded.
- [ ] Submitted public reference recorded in the packet.
