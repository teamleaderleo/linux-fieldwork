# BuildKit unused-context carrier status

- Controlled fork: `teamleaderleo/buildkit`
- Test branch: `research/unused-context-lazy-load`
- Test-only head: `4024335d0e905d1206786644d8f363336d4678ec`
- Exact snapshot base: `linux-fieldwork/upstream-master-snapshot-2026-08-03`
- Exact canonical base commit: `275d6864ff0ce91a06225af5f5b012887bd257cf`
- Internal draft PR: `teamleaderleo/buildkit#2`
- PR state at latest review: open, draft, mergeable
- Product source changes: none
- Local source-only receipt: exact test file produces an empty `gofmt -d`
- Hosted static receipt: Linux Fieldwork run `31012029092`, job `92326394200`, success
- Hosted static coverage: exact checkout identity, canonical-base ancestry, `git diff --check`, canonical formatting, vendored Dockerfile package compile, and clean checkout all passed
- Hosted runtime receipt: pending
- Submitted reviews/comments: none observed on controlled PR #2
- Expected baseline: metadata-only subtest fails because the sentinel main context is accessed
- Positive controls: local `COPY` and default-context bind mount must access the sentinel
- External contact: none

The exact repaired test carrier now compiles in the repository package and passes formatting and ancestry checks. This remains a compile-only receipt. The next technical gate is the focused Dockerfile integration execution that distinguishes the metadata-only baseline from the two used-context controls, followed by provenance-absence checking only after lazy transfer behavior is demonstrated.
