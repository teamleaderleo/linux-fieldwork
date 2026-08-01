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

This change retained original path globs beside their compiled matchers and used the glob's literal prefix to identify excluded directory or symlink parents that can lead to a later included member. Component-bounded comparisons preserved conservative wildcard behavior while keeping `/usr` and `/usr2` distinct.

A focused regression covered exact includes, wildcard descendants, character classes, a component-boundary control, and a symlink parent while checking mode, uid, gid, mtime, link target, and PAX metadata.

### Before

Filtering with `--path-exclude='/*' --path-include='/usr/bin/tool'` emitted only `usr/bin/tool`. Extraction recreated `usr/` and `usr/bin/` with default modes and lost their explicit archive metadata.

### After

The filtered archive retained `usr`, `usr/bin`, and `usr/bin/tool`. Parent metadata survived. The symlink case retained the explicit symlink entry and its target and metadata.

### Implementation

`PathFilterAction` stores `(destination, glob, compiled_regex)`. The ordinary rule loop continues to use the compiled regex. The excluded directory/symlink branch derives a literal prefix from the original glob and retains a member when its path and the prefix are equal or one is a component-bounded ancestor of the other. An empty fixed prefix preserves conservative leading-wildcard behavior.

### Tests

Executed on exact current `tarfilter` source:

- baseline focused test: expected failure, only leaf emitted;
- patched focused test: five cases pass;
- Python compilation, shell syntax, and diff whitespace checks pass.

Pending on a full canonical checkout:

- `CMD=./mmdebstrap ./coverage.py tarfilter-parent-metadata`;
- Black and broader repository gates.

### Compatibility

Ordinary rule precedence and matcher behavior remain unchanged. The change affects only the existing excluded-directory/symlink parent-retention path.

## Proposed commits or patch order

1. `tarfilter: retain parent metadata for nested path includes`

## Reviewer notes

The two comparison directions serve different patterns: exact includes need the include prefix to recognize ancestors; a wildcard before the current path component needs the current path to recognize the fixed prefix. `/` boundaries prevent lexical prefix aliases.

## Submission checklist

- [ ] Full candidate checkout created from current upstream base.
- [ ] Complete upstream diff reviewed.
- [x] Baseline loses and candidate passes focused controls.
- [ ] Upstream-native focused test passes.
- [x] Public overlap reviewed on 2026-08-01.
- [ ] Fork/branch delivery path exists.
- [ ] Explicit authorization recorded.
- [ ] Public PR and submitted identity recorded.
