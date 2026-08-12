# Agent Instructions

Read [`README.md`](README.md), [`START_HERE.md`](START_HERE.md), [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md), [`FIELD_GUIDE.md`](FIELD_GUIDE.md), [`MAINTAINER_COMMUNICATION.md`](MAINTAINER_COMMUNICATION.md), and [`SOURCE_BRANCH_HYGIENE.md`](SOURCE_BRANCH_HYGIENE.md) before doing repository or owned-fork source work.

## Upstream greenlight

Upstream contact remains deliberate by default. When the human says `upstream greenlight`, treat that natural-language phrase as explicit authorization for the current upstream repository and interaction reasonably clear from the conversation. Capitalization and an exact template are not required. If the repository or action is genuinely ambiguous or materially broader than the surrounding context supports, ask before acting.

A greenlight is bounded to that upstream interaction. It does not imply merge, release, deployment, credentials, spending, private-data access, or unrelated authority. A later human instruction can narrow or revoke it.

## Source branch guardrails

These rules are mandatory for owned-fork candidates that may later be offered upstream:

- Keep candidate branches limited to the intended product change and its real tests or documentation.
- For simple source edits, edit the branch directly with ordinary Git operations. Do not invent GitHub Actions materializers, trigger files, self-modifying workflows, carrier commits, or other machinery merely to write the change.
- Temporary execution machinery must live on a separate disposable branch or in Linux Fieldwork and must not survive in candidate history.
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
- Creating or editing an owned-fork branch does not authorize upstream issues, pull requests, comments, reviews, reactions, emails, or other contact.

If a normal local Git operation can produce the desired branch, prefer it over repository automation. Do not add ceremony that exists only to compensate for a tool limitation.
