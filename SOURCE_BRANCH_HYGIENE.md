# Source Branch Hygiene

These rules apply **only when the human has designated a branch or commit series in an owned fork as a candidate for possible upstream review**.

They do not constrain ordinary internal research. Until that designation occurs, owned-fork research branches may contain diagnostic instrumentation, temporary workflows, failed experiments, throwaway fixtures, generated material, intermediate commits, or other research churn that helps answer the investigation.

Once a branch is designated as an upstream candidate, clean it up according to the rules below. The human controls the boundary between internal research and upstream-candidate preparation.

## Keep source candidates boring

A source candidate branch should contain only the product change and the tests or documentation that belong with that change.

For a trivial source edit, make the edit directly on the candidate branch with ordinary Git operations. Do not introduce a GitHub Actions materializer, trigger file, carrier commit, transformer, self-modifying workflow, or other execution machinery merely to write the source change.

Temporary execution machinery may exist on internal research branches, but it must never become part of the candidate branch's surviving history.

Before presenting a candidate branch for review, compare it against the intended upstream base and require that the diff contains only the intended product files.

## Treat an open upstream PR head as a publication branch

Once an owned-fork candidate branch is the head of an open upstream pull request, every push to that branch updates the upstream-visible PR head and may trigger CI, checks, notifications, or reviewer activity.

Do not use a live PR head for known intermediate work, connector experiments, repair commits, or edits that are expected to need cleanup. Do that work locally or on a separate scratch branch created from the current PR head. Inspect, test, squash, amend, or rebuild the result there, then move or push one coherent reviewable revision onto the live PR branch.

Normal review-driven follow-up pushes are expected. The goal is not to avoid updating an open PR; it is to avoid publishing revisions that are already known to be temporary.

When the available tooling can only edit remote GitHub branches, create a scratch branch by default. Before advancing the live PR head, compare the finished candidate against the previous PR head and verify that the diff contains only the intended review response.

## Never put issue or pull-request references in commit messages

Do not include external issue numbers, pull-request numbers, shorthand references, or URLs in candidate commit subjects or bodies.

This includes forms such as:

- `#5388`
- `Fixes #5388`
- `opencontainers/runc#5388`
- direct or redirect GitHub issue and pull-request URLs

Put issue-closing syntax and external references in the pull-request body instead, after upstream interaction has been explicitly authorized.

A source commit message should describe the code change itself. Keep required project trailers such as `Signed-off-by` when the target project requires them.

## Use the contributor's configured identity for sign-offs

When the target project requires DCO or another `Signed-off-by` trailer, first verify the project's contribution instructions and then use the contributor's configured Git identity.

Prefer ordinary Git commands such as:

```text
git config user.name
git config user.email
git commit -s
```

For an amended commit where the author identity also needs to match the configured identity, use normal Git author-reset/sign-off behavior rather than constructing the trailer by hand.

Never manufacture, infer, or substitute a sign-off identity from GitHub account metadata. In particular, do not synthesize a `users.noreply.github.com` address from a username or numeric account ID, and do not replace a configured real name with a GitHub login.

If the configured Git identity is unavailable to the current execution environment, do not guess. Leave the candidate unsigned for the human to sign locally, or provide the exact `git commit -s` / amend command needed to finish it.

A privacy-preserving noreply address is acceptable only when it is already the contributor's configured or explicitly chosen Git identity. The tooling must not choose it on the contributor's behalf.

## One logical change, one clean history

For a small upstream candidate, prefer one clean commit when the change is naturally atomic.

Do not leave behind:

- temporary materialization commits;
- trigger commits;
- carrier setup or cleanup commits;
- issue-number bookkeeping commits;
- failed automation attempts;
- intermediate rename or repair commits that can be cleanly folded into the candidate.

If temporary commits were created during research, rebuild or squash the candidate before presenting it. The final branch should read as if the intended product change had been made directly from the correct upstream base.

## Preserve repository commit-message policy

Before publishing an amended, squashed, or rebuilt candidate commit, preserve the target repository's commit-message rules as carefully as its source rules. Check contribution guidance and any local `gitlint`, `commitlint`, or equivalent configuration when available.

Editorless commands need special care. `git commit -m` does not reflow prose to a repository's preferred width; a paragraph supplied as one shell argument remains one physical line unless explicit newlines are embedded. If the repository enforces a 72-column body, either provide those line breaks directly or use a safe formatter before committing.

When a concrete line limit is known, verify it mechanically instead of counting by eye. For a 72-column policy, for example:

```text
git log -1 --format=%B | awk 'length($0) > 72 { print NR ":" length($0) ":" $0 }'
```

An empty result means no commit-message line exceeds 72 characters. Prefer the repository's own lint command when one exists because it may enforce additional subject, trailer, or formatting rules.

CI should normally validate submitted commit messages, not silently rewrite them. Rewrapping a commit message creates a different commit object and SHA; for signed commits it also requires a new signature. Treat a commit-message lint failure as a request to amend locally, re-sign if required, and publish the corrected revision deliberately.

## External interaction remains separate

Creating, editing, testing, or heavily iterating on an owned-fork research branch is not permission to contact upstream.

Do not open, edit, comment on, review, react to, or otherwise interact with an upstream issue or pull request unless that external action has been explicitly authorized. Preparing source, tests, comparison data, draft wording, and CI evidence in owned repositories is allowed under the owned-fork research authority; publication is a separate decision.

## Final source-candidate check

Before handing a candidate to a human for upstream submission, verify all of the following:

1. The branch is based on the intended current upstream revision.
2. The diff contains only intended product/test/documentation files.
3. No temporary workflow, trigger, receipt, carrier, or Fieldwork-only file remains.
4. The commit history is minimal and reviewable.
5. Commit messages contain no issue or pull-request numbers, shorthand references, or URLs.
6. Required project trailers such as DCO sign-off are present and use the contributor's configured or explicitly chosen Git identity.
7. No sign-off name or email was inferred or synthesized from provider account metadata.
8. Issue-closing syntax, if desired, appears only in the pull-request body.
9. No upstream interaction has occurred beyond what the human explicitly authorized.
10. If the branch is already the head of an open upstream PR, exploratory work happened elsewhere and the pushed revision is coherent and reviewable.
11. The final commit message satisfies the target repository's lint and wrapping policy, including any editorless `-m` content.