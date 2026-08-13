# Source Branch Hygiene

These rules apply whenever Linux Fieldwork prepares a candidate change in an owned fork for possible upstream review.

## Keep source branches boring

A source candidate branch should contain only the product change and the tests or documentation that belong with that change.

For a trivial source edit, make the edit directly on the candidate branch with ordinary Git operations. Do not introduce a GitHub Actions materializer, trigger file, carrier commit, transformer, self-modifying workflow, or other execution machinery merely to write the source change.

Temporary execution machinery belongs on a separate disposable branch or in Linux Fieldwork. It must never become part of the candidate branch's surviving history.

Before presenting a candidate branch for review, compare it against the intended upstream base and require that the diff contains only the intended product files.

## Never put issue or pull-request references in commit messages

Do not include external issue numbers, pull-request numbers, shorthand references, or URLs in commit subjects or bodies.

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

A GitHub-resolved author or committer account is not proof of the raw Git identity. DCO verification must inspect the commit object's author and committer name/email directly, for example:

```text
git show --no-patch --format=fuller HEAD
git log -1 --format='%an <%ae>%n%cn <%ce>%n%B'
```

Require the raw author, raw committer, and every required `Signed-off-by:` identity to agree with the contributor's configured or explicitly chosen identity.

If the configured Git identity is unavailable to the current execution environment, do not guess. Leave the candidate unsigned for the human to sign locally, or provide the exact `git commit -s` / amend command needed to finish it.

If the available commit-writing API or connector cannot explicitly set the required raw author/committer identity and independently expose or verify the resulting raw metadata, do not use it to create, squash, amend, rebase, or rebuild the final DCO-bearing submission commit. Stop at preparation and leave the final commit operation to ordinary Git or the human.

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

If temporary commits were created while preparing the branch, rebuild or squash the candidate before presenting it. The final branch should read as if the intended product change had been made directly from the correct upstream base.

Every operation that creates a new commit object reopens final identity verification. This includes squash, amend, rebase, cherry-pick, clean-base rebuild, and API commit recreation. An unchanged source tree does not preserve authorship metadata or DCO validity automatically.

## External interaction remains separate

Creating or editing an owned-fork branch is not permission to contact upstream.

Do not open, edit, comment on, review, or otherwise interact with an upstream issue or pull request unless that external action has been explicitly authorized. Preparing a clean branch and draft wording is allowed when repository authority permits it; publication is a separate decision.

## Final source-branch check

Before handing a candidate to a human for upstream submission, verify all of the following:

1. The branch is based on the intended current upstream revision.
2. The diff contains only intended product/test/documentation files.
3. No temporary workflow, trigger, receipt, carrier, or Fieldwork-only file remains.
4. The commit history is minimal and reviewable.
5. Commit messages contain no issue or pull-request numbers, shorthand references, or URLs.
6. Required project trailers such as DCO sign-off are present and use the contributor's configured or explicitly chosen Git identity.
7. Raw Git author and committer name/email were inspected directly and match the intended contributor identity; GitHub account association alone is not sufficient.
8. No sign-off name or email was inferred or synthesized from provider account metadata.
9. Any history rewrite was followed by a fresh raw author/committer/trailer check on the new exact SHA.
10. Issue-closing syntax, if desired, appears only in the pull-request body.
11. No upstream interaction has occurred beyond what the human explicitly authorized.
