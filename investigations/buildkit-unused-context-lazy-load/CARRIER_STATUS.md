# BuildKit unused-context carrier status

- Controlled fork: `teamleaderleo/buildkit`
- Test branch: `research/unused-context-lazy-load`
- Test-only head: `67c480358d6f5d1fd2e3d41bb3fd460e3957210e`
- Exact snapshot base: `linux-fieldwork/upstream-master-snapshot-2026-08-03`
- Exact canonical base commit: `275d6864ff0ce91a06225af5f5b012887bd257cf`
- Internal draft PR: `teamleaderleo/buildkit#2`
- PR state at latest review: open, draft, mergeable
- Product source changes: none
- Local source-only receipt: exact test file produces an empty `gofmt -d`
- Local package compile receipt: unavailable; execution container DNS failed before repository clone
- Hosted static receipt: queued in Linux Fieldwork run `30802233175`, job `91649238210`
- Hosted runtime receipt: pending
- Submitted reviews/comments: none observed
- Expected baseline: metadata-only subtest fails because the sentinel main context is accessed
- Positive controls: local `COPY` and default-context bind mount must access the sentinel
- External contact: none

The local formatting receipt establishes only canonical Go formatting for the exact added file. The queued hosted job still owns ancestry, diff, vendored package compilation, and clean-checkout validation. A compile-only pass will not establish the expected runtime access matrix or provenance absence.
