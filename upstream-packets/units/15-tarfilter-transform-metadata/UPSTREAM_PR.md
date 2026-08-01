# Upstream pull request draft

Status: `DRAFT`  
Proposed destination: `josch/mmdebstrap` Forgejo pull request  
Proposed base branch: `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`  
Controlled fork: `teamleaderleo/mmdebstrap`  
Candidate branch: `linux-fieldwork/unit-15-tarfilter-transform-metadata`  
Candidate head: `505bf81079a3b76c7d56bffa8097c1b5a494898e`  
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

A project-native regression is included as `tests/tarfilter-transform-metadata` and registered in `coverage.txt`.

Direct execution on Python 3.13.5 and GNU tar 1.35 establishes:

- the exact baseline fails with status `1` at the first-replacement assertion;
- the exact candidate passes twice with status `0`;
- ordinary/global, case-insensitive, whole-match, escaped-delimiter, default/`S` scope, hard-link extraction, PAX regeneration, numeric selector, and non-ASCII rejection cases pass;
- Python compile and POSIX shell syntax checks pass;
- no matching temporary directories survive.

The broader packet-owned matrix produced identical PASS receipts across repeated runs.

Execution through the complete `coverage.py` runner, shellcheck, shfmt, package/build gates, and hosted CI remains before this draft can become ready.

### Compatibility

The patch keeps the existing Python regular-expression pattern dialect. GNU basic/extended regex translation and broader transform grammar remain outside this change. Unsupported or duplicate retained flags fail explicitly.

## Current controlled-fork diff

```text
base and merge base: 77ec9be5417ee44c96343d2347145585da1b1f94
head: 505bf81079a3b76c7d56bffa8097c1b5a494898e
ahead: 3
behind: 0
coverage.txt                         +2   -0
tarfilter                          +179  -23
tests/tarfilter-transform-metadata +250  -0
```

Current commits:

1. `f7833615824ad99023c21a495840d10f64c6401a` — source candidate
2. `f7337a7d2f33d280c8e5b1576dd729f4d076c13a` — native regression
3. `505bf81079a3b76c7d56bffa8097c1b5a494898e` — test registration

This three-commit internal form preserves exact source/test/registration identities. Final upstream commit organization remains a review decision.

## Reviewer notes

Focus review on:

- occurrence counting for the member name and each selected link target;
- default `rsh` scope and uppercase opt-outs;
- hard-link target rewriting during component stripping;
- PAX authority after logical name or link-target changes;
- whether the current source change should remain one semantic commit.

## Submission checklist

- [x] Clean source patch generated from the exact baseline.
- [x] Controlled fork and exact canonical snapshot branch exist.
- [x] Candidate source branch exists at an exact head.
- [x] Native test and `coverage.txt` registration are committed.
- [x] Baseline regression loses and candidate passes directly.
- [x] Focused GNU tar differential matrix passes repeatedly.
- [x] Python and POSIX shell syntax pass.
- [x] Cleanup and immediate rerun pass.
- [x] Complete three-file fork diff boundary reviewed.
- [x] Active equivalent work rechecked on 2026-08-01.
- [ ] Selected test passes through the complete `coverage.py` runner.
- [ ] Shellcheck and shfmt pass.
- [ ] Relevant package/build gates pass.
- [ ] Hosted CI passes if the controlled fork provides an applicable workflow.
- [ ] Final upstream commit organization reviewed.
- [ ] Explicit authorization recorded.
- [ ] Public reference and exact submitted head recorded after submission.

## Authority note

This is an internal draft. No upstream object has been created or updated.
