# Source Branch Hygiene

These rules apply **only when the human has designated a branch or commit series in an owned fork as a candidate for possible upstream review**.

They do not constrain ordinary internal research. Until that designation occurs, owned-fork research branches may contain diagnostic instrumentation, temporary workflows, failed experiments, throwaway fixtures, generated material, intermediate commits, or other research churn that helps answer the investigation.

Once a branch is designated as an upstream candidate, clean it up according to the rules below. The human controls the boundary between internal research and upstream-candidate preparation.

## Keep source candidates boring

A source candidate branch should contain only the product change and the tests or documentation that belong with that change.

For a trivial source edit, make the edit directly on the candidate branch with ordinary Git operations. Do not introduce a GitHub Actions materializer, trigger file, carrier commit, transformer, self-modifying workflow, or other execution machinery merely to write the source change.

Temporary execution machinery may exist on internal research branches, but it must never become part of the candidate branch's surviving history.

Before presenting a candidate branch for review, compare it against the intended upstream base and require that the diff contains only the intended product files.

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