# BuildKit unused-context carrier status

- Controlled fork: `teamleaderleo/buildkit`
- Test branch: `research/unused-context-lazy-load`
- Test-only head: `67c480358d6f5d1fd2e3d41bb3fd460e3957210e`
- Exact snapshot base: `linux-fieldwork/upstream-master-snapshot-2026-08-03`
- Exact canonical base commit: `275d6864ff0ce91a06225af5f5b012887bd257cf`
- Internal draft PR: `teamleaderleo/buildkit#2`
- Product source changes: none
- Local compile receipt: unavailable; execution container DNS failed before clone
- Hosted static receipt: pending
- Hosted runtime receipt: pending
- Workflow runs observed immediately after PR creation: none
- Submitted reviews: none observed at creation
- Expected baseline: metadata-only subtest fails because the sentinel main context is accessed
- Positive controls: local `COPY` and default-context bind mount must access the sentinel
- External contact: none

A missing or queued workflow is not a passing result. A compile-only pass will establish syntax, formatting, ancestry, and package compilation; it will not establish the expected runtime access matrix.
