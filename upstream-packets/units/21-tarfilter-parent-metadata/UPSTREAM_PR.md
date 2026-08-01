# Upstream pull request draft

Status: `DRAFT`  
Proposed destination: canonical mmdebstrap Forgejo repository  
Proposed base branch: `main`  
Candidate branch or patch series: `NEEDS FORK`; retained patch `patches/0001-tarfilter-retain-parent-metadata.patch`  
External contact authorized: `false`

## Proposed title

tarfilter: retain parent metadata for nested path includes

## Draft

### Summary

This change retained original path globs beside their compiled matchers and used the glob's literal prefix to identify excluded directory or symlink parents that can lead to a later included member. Component-bounded comparisons preserved conservative wildcard behavior without treating names such as `/usr` and `/usr2` as the same path prefix.

A focused regression covered exact includes, wildcarded descendants, character classes, and the component-boundary control while checking mode, uid, gid, mtime, and PAX metadata.

### Before

Filtering an archive with `--path-exclude='/*' --path-include='/usr/bin/tool'` emitted only `usr/bin/tool`. Extraction recreated `usr/` and `usr/bin/` with default modes and lost their explicit archive metadata.

### After

The filtered archive retained `usr`, `usr/bin`, and `usr/bin/tool`. Parent mode, ownership fields, timestamp, and PAX headers survived the filter and extraction used the explicit parent modes.

### Implementation

`PathFilterAction` now stores `(destination, glob, compiled_regex)`. The ordinary rule loop still matches with the compiled regex. The excluded directory/symlink branch derives a literal prefix from the original glob and retains the member when the current path and prefix are equal or one is a component-bounded ancestor of the other. An empty fixed prefix keeps the conservative behavior for leading wildcards.

### Tests

Locally executed before fork creation:

- baseline/candidate PAX archive matrix on Python 3.13.5 and GNU tar 1.35;
- exact, wildcard, character-class, component-boundary, unrelated, and leading-wildcard relation cases;
- proposed shell regression against a focused candidate executable;
- patch application to an exact-context fixture, Python compilation, shell syntax, cleanup, and immediate rerun.

The full upstream `coverage.py`, `coverage.sh`, formatting, package, and autopkgtest gates remain to be run on the fork-backed candidate head.

### Compatibility

Last-match-wins filtering for ordinary members is unchanged. Parent retention remains conservative, matching dpkg's documented safety policy. The change affects only excluded directories and symlinks with a later include relation.

### Related issue

No public upstream issue exists at draft time. Add one only if project workflow requires it.

## Proposed commits or patch order

1. `tarfilter: retain parent metadata for nested path includes`

## Reviewer notes

The two-direction comparison is deliberate. Exact includes need the include prefix to recognize its ancestors; wildcard patterns whose metacharacter occurs before the current directory need conservative recognition in the other direction. Component separators prevent plain string-prefix aliases.

## Submission checklist

- [ ] Candidate rebased onto the current intended upstream base.
- [ ] Complete upstream diff reviewed on a controlled fork.
- [x] Baseline regression loses and focused candidate passes locally.
- [ ] Upstream-native focused tests pass.
- [x] Cleanup and immediate rerun pass locally.
- [x] Active equivalent work checked on 2026-07-31; recheck before submission.
- [ ] Fork/branch delivery path exists.
- [x] Draft contains no Linux Fieldwork-only routing or private data in its proposed body.
- [ ] Explicit authorization recorded.
- [ ] Public PR and exact submitted head recorded after submission.
