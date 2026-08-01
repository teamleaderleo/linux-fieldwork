# Upstream pull request draft

Status: `DRAFT`  
Proposed destination: `josch/mmdebstrap` Forgejo pull request  
Proposed base branch: `main`  
Candidate branch or patch series: `NEEDS FORK` / `NEEDS BRANCH`; packet patch `patches/0001-tarfilter-transform-metadata.patch`  
External contact authorized: `false`

## Proposed title

`tarfilter: keep transform targets and PAX paths consistent`

## Draft

### Summary

This change makes the supported `tarfilter --transform` substitution behavior consistent across member names, hard-link targets, symlink targets, and PAX path metadata. It implements first-only replacement by default, global replacement with `g`, case-insensitive matching, whole-match `&`, tested replacement escapes, target scopes, and numeric occurrence selectors.

Component stripping now updates retained hard-link targets. Changed logical names discard stale PAX `path` or `linkpath` values so long metadata is regenerated from the corrected fields.

### Before

- `s/a/b/` changes `a/a` to `b/b`.
- `g` and numeric occurrence selectors are rejected.
- default transforms rename members while leaving hard-link and symlink target text stale.
- stripping a prefix can leave a hard link pointing at the removed name.
- long PAX `path` and `linkpath` values can override the requested output names.

### After

- ordinary, global, case-insensitive, whole-match, escaped-delimiter, and numeric cases match GNU tar for the tested subset;
- default target scope is `rsh`, with uppercase scope flags acting as opt-outs;
- transformed and stripped hard links extract successfully and retain inode identity;
- long PAX path and linkpath values reflect the corrected logical names.

### Implementation

The transform parser records the delimiter-aware pattern and replacement, case/global flags, numeric selector, and target scopes. A substitution helper counts matches independently for each selected value. The archive loop applies the transform to the requested member and link fields, then invalidates stale PAX names when those fields changed. The strip path applies the same hard-link/PAX consistency rule.

### Tests

Executed on the exact candidate source with Python 3.13.5 and GNU tar 1.35:

- baseline losing controls for ordinary replacement, `g`, stale link targets, stale PAX paths, and numeric predecessor rejection;
- GNU tar differential replacement matrix;
- default and uppercase-`S` target-scope matrix;
- hard-link extraction and inode identity;
- 120-byte PAX path/linkpath regeneration;
- numeric, numeric-plus-global, zero, ordering, repeated decimal runs, link-target counting, and non-ASCII rejection;
- cleanup and immediate rerun with identical receipts.

Upstream-native repository tests, formatting, and package gates remain to be executed on the final branch before this draft can become ready.

### Compatibility

The patch keeps the existing Python regular-expression pattern dialect. GNU basic/extended regex translation and broader transform grammar remain outside this change. Unsupported or duplicate retained flags fail explicitly.

## Proposed commits or patch order

Current default:

1. `tarfilter: keep transform targets and PAX paths consistent`

Possible ordered series after upstream-native review:

1. `tarfilter: implement retained substitution and occurrence semantics`
2. `tarfilter: keep link targets and PAX paths consistent`

## Reviewer notes

Please focus on the shared occurrence state for member names and each selected link target, default `rsh` scope, uppercase scope opt-outs, hard-link strip behavior, and PAX authority after logical-name changes.

## Submission checklist

- [x] Clean patch generated from the exact baseline.
- [x] Baseline regression loses and candidate passes.
- [x] Focused GNU tar differential matrix passes repeatedly.
- [x] Cleanup and immediate rerun pass.
- [x] Active equivalent work rechecked on 2026-08-01.
- [ ] Candidate applied and committed in a full current-upstream checkout.
- [ ] Upstream-native focused tests pass.
- [ ] Formatting/lint and relevant package gates pass.
- [ ] Complete final upstream diff reviewed.
- [ ] Fork and branch exist.
- [ ] Explicit authorization recorded.
- [ ] Public reference and exact submitted head recorded after submission.
