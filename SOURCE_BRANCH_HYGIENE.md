# Source Branch Hygiene

These rules begin **only when the human designates a branch or commit series in an owned fork as a candidate for possible upstream review**. Ordinary internal research remains free to use diagnostic instrumentation, temporary workflows, failed experiments, generated material, throwaway fixtures, intermediate commits, and other useful churn. The human controls the transition from research to upstream-candidate preparation.

## Candidate cleanliness

Once designated, keep the candidate boring:

- Base it on the intended upstream revision and limit the surviving diff to the product change plus its real tests or documentation.
- Make ordinary source edits directly with normal Git operations. Do not introduce materializers, trigger files, carrier commits, self-modifying workflows, or similar machinery merely to write the candidate.
- Keep all temporary execution machinery on research or scratch branches and out of the candidate's surviving history.
- For a small atomic change, prefer one clean commit. Squash or rebuild away setup, cleanup, failed-automation, bookkeeping, intermediate rename, and repair commits before review.
- Compare the finished candidate against the intended upstream base and inspect every changed path before presenting it.

## Open upstream pull-request heads

Once a candidate branch is the head of an open upstream pull request, every push changes the upstream-visible revision and may trigger CI, notifications, or reviewer work. Do known intermediate work locally or on a separate scratch branch from the current PR head. Inspect, test, squash, amend, or rebuild there, then advance the live head with one coherent reviewable revision.

Review-driven follow-up pushes are expected. When tooling can edit only remote branches, use a scratch branch by default and compare the finished candidate with the previous PR head before advancing it.

## Commit messages and external references

Candidate commit subjects and bodies contain no external issue or pull-request numbers, shorthand references, or direct or redirect URLs. This includes `#5388`, `Fixes #5388`, and `OWNER/REPO#5388`. Put issue-closing syntax and external references in the pull-request body only after that upstream interaction is explicitly authorized.

Describe the code change itself and preserve required project trailers. Check the target repository's contribution and commit-message rules before publishing an amended, squashed, or rebuilt commit. `git commit -m` does not reflow prose; when a line limit is known, verify it mechanically or use the repository's own lint. A lint failure calls for a deliberate local amend and re-signing when required, not CI that silently rewrites commit identity.

For a known 72-column policy, one mechanical check is:

```text
git log -1 --format=%B | awk 'length($0) > 72 { print NR ":" length($0) ":" $0 }'
```

## Contributor identity and sign-off

[`CONTRIBUTOR_IDENTITY.md`](CONTRIBUTOR_IDENTITY.md) owns identity provenance. For work intended for upstream submission, obtain the contributor name and email explicitly from the human and configure exactly that identity; verify any existing Git configuration against it. When the target requires DCO or another `Signed-off-by` trailer, verify the project requirement and prefer normal Git behavior such as:

```text
git config user.name
git config user.email
git commit -s
```

Never infer, manufacture, or substitute a sign-off identity from repository history, account metadata, a GitHub login, or a numeric account ID. A `users.noreply.github.com` address is valid only when the human explicitly chose it. If the required identity is unavailable, leave the candidate for the human to sign locally and provide the exact amend or `git commit -s` command needed.

Before exposing a compare link or recommending submission, verify the final commit's resolved author, committer, and every `Signed-off-by` trailer. When amending authorship, use normal Git author-reset/sign-off behavior instead of constructing trailers by hand.

## External interaction stays separate

Candidate preparation grants no upstream-contact authority. Opening, editing, commenting on, reviewing, reacting to, or otherwise interacting with an upstream issue or pull request requires the deliberate authorization defined in [`AGENTS.md`](AGENTS.md). Third-party reference hygiene is owned by [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md#external-github-backlinks).

## Handoff check

Before handing a candidate to a human for upstream submission, verify:

1. intended upstream base and only intended product/test/documentation paths in the diff;
2. no temporary workflow, trigger, receipt, carrier, or Fieldwork-only file in surviving history;
3. minimal reviewable commits whose messages satisfy target policy and contain no issue/PR references or URLs;
4. required trailers use the contributor's valid configured or explicitly chosen identity, with no identity inferred from provider metadata;
5. any issue-closing syntax appears only in the pull-request body after contact authorization;
6. upstream interaction stayed within explicit authority;
7. an open upstream PR head received only coherent reviewable revisions, with exploratory work done elsewhere.
