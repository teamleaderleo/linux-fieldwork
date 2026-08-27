# Agent Instructions

Read [`README.md`](README.md), [`START_HERE.md`](START_HERE.md), [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md), [`FIELD_GUIDE.md`](FIELD_GUIDE.md), [`MAINTAINER_COMMUNICATION.md`](MAINTAINER_COMMUNICATION.md), and [`SOURCE_BRANCH_HYGIENE.md`](SOURCE_BRANCH_HYGIENE.md) before doing repository or owned-fork source work.

## Owned-fork research authority

The human owner has explicitly authorized broad autonomous research work in repositories and forks owned by `teamleaderleo`.

Unless a later instruction narrows or revokes this authority, agents may create, edit, delete, commit, and iterate on code, tests, instrumentation, workflows, experiment branches, fixtures, documentation, CI jobs, and other research material in owned repositories and owned forks when doing so advances the current investigation.

Internal research branches are allowed to be messy. Agents may use temporary commits, diagnostic instrumentation, experimental workflows, generated test material, carrier branches, throwaway fixtures, and other execution machinery when useful. Do not spend time preserving upstream-ready history during ordinary internal churn.

### Execution and GitHub Actions authority

For internal research, ordinary repository writes are expected work rather than a special boundary. Agents may use normal Git operations or the GitHub contents API to write files and commits in owned repositories and owned forks. They may also create, edit, run, repair, and remove GitHub Actions workflows for experiments, including build matrices, diagnostic jobs, temporary instrumentation, caches, artifacts, workflow-dispatch inputs, and branch-triggered runs.

Prefer the simplest mechanism that gets evidence. A disposable Actions workflow is a valid experimental harness when it gives access to a useful architecture, clean environment, dependency set, or reproducible runtime. It is fine for an internal workflow or branch to fail repeatedly while narrowing an issue; preserve useful receipts and distinguish harness failures from product failures.

Agents do not need separate human confirmation for each ordinary internal file edit, commit, branch, test run, workflow change, or Actions experiment covered by this authority. When one experimental route is blocked by tooling, use another normal repository or Actions route rather than treating the owned repository as read-only.

This authority does **not** publish anything upstream. The human owns the boundary where research is converted into an upstream submission. An owned-fork experiment must not be represented as an upstream-authored or upstream-ready contribution merely because it exists.

Backlink and external-interaction hygiene still applies. Do not create third-party GitHub backlinks or timeline events accidentally. When controlled interaction text must mention a third-party GitHub issue, pull request, or commit, use the repository's redirect-link convention. Do not comment, review, react, open issues or pull requests, or otherwise contact a third-party upstream unless the human has authorized that upstream interaction.

A later human instruction can designate a specific branch or commit series as an **upstream candidate**. Only then do the candidate-history, sign-off, and source-branch rules in [`SOURCE_BRANCH_HYGIENE.md`](SOURCE_BRANCH_HYGIENE.md) become mandatory for that candidate.

## Upstream greenlight

Upstream contact remains deliberate by default. When the human says `upstream greenlight`, treat that natural-language phrase as explicit authorization for the current upstream repository and interaction reasonably clear from the conversation. Capitalization and an exact template are not required. If the repository or action is genuinely ambiguous or materially broader than the surrounding context supports, ask before acting.

A greenlight is bounded to that upstream interaction. It does not imply merge, release, deployment, credentials, spending, private-data access, or unrelated authority. A later human instruction can narrow or revoke it.

## Upstream-candidate guardrails

These rules apply only after the human has designated work as an upstream candidate:

- Keep candidate branches limited to the intended product change and its real tests or documentation.
- For simple source edits, edit the branch directly with ordinary Git operations. Do not invent GitHub Actions materializers, trigger files, self-modifying workflows, carrier commits, or other machinery merely to write the change.
- Temporary execution machinery must not survive in candidate history.
- Never put external issue numbers, pull-request numbers, shorthand references, or URLs in commit subjects or bodies. This includes `#123`, `Fixes #123`, `OWNER/REPO#123`, and direct or redirect issue/PR URLs.
- Put issue-closing syntax and external references in the pull-request body only, after that upstream interaction is explicitly authorized.
- Preserve required project trailers such as `Signed-off-by` when applicable.
- When DCO or another sign-off is required, use the contributor's configured or explicitly chosen Git identity. Prefer `git commit -s` and normal amend/reset-author behavior.
- Never infer or synthesize a sign-off name or email from GitHub account metadata. Do not manufacture a `users.noreply.github.com` address from a login or numeric account ID.
- A noreply address is acceptable only when it is already the contributor's configured or explicitly chosen Git email.
- If the configured Git identity is unavailable, do not guess; leave the candidate for the human to sign locally and provide the exact command needed.
- For a small atomic fix, prefer one clean commit. Squash or rebuild away temporary setup, cleanup, rename, repair, and failed-automation commits before human review.
- Before presenting a candidate, compare against the intended upstream base and verify that only the intended files remain.
- A commit reference that creates a GitHub backlink or timeline event counts as external interaction. Do not create such references without explicit authorization.

If a normal local Git operation can produce the desired candidate branch, prefer it over repository automation. This preference does not restrict internal research branches.
