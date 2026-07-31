# Upstream pull request draft

Status: `DRAFT | READY FOR AUTHORIZATION | SENT`  
Proposed destination: `...`  
Proposed base branch: `...`  
Candidate branch or patch series: `...`  
External contact authorized: `false`

Write this as accomplished behavior. Do not use imperative “should” language for the summary of the change.

## Proposed title

...

## Draft

### Summary

This change ...

Describe the resulting behavior, the former failure, and the bounded implementation.

### Before

Describe the concrete baseline result.

### After

Describe the corrected observable behavior.

### Implementation

Explain the main source changes and why they form one reviewable unit or ordered series.

### Tests

List upstream-native tests and focused regressions that ran on the exact candidate head. Name unexecuted gates explicitly.

### Compatibility

Describe preserved behavior, intentional changes, supported modes, and known exclusions.

### Related issue

Link an upstream issue only when it exists or the project requires one. Do not include private or internal-only references in the submitted version.

## Proposed commits or patch order

1. `...`
2. `...`

## Reviewer notes

Call out subtle ownership, lifecycle, metadata, portability, or compatibility choices that deserve focused review.

## Submission checklist

- [ ] Candidate rebased onto the current intended upstream base.
- [ ] Complete upstream diff reviewed.
- [ ] Baseline regression fails and candidate passes.
- [ ] Upstream-native focused tests pass.
- [ ] Cleanup and immediate rerun pass where relevant.
- [ ] Active equivalent work rechecked.
- [ ] Fork/branch or patch-series delivery path exists.
- [ ] Draft contains no Linux Fieldwork-only routing or private data.
- [ ] Explicit authorization recorded.
- [ ] Public PR/MR/message and exact submitted head or patch identity recorded after submission.
