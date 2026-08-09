# Contributor identity guardrail

Contributor identity is not inferred metadata.

For any commit intended for upstream submission:

- never copy `user.name`, `user.email`, author, committer, or `Signed-off-by` identity from the base commit, a nearby upstream commit, a repository owner, or a GitHub username;
- obtain the contributor name and email explicitly from the human who will submit the contribution;
- treat `git commit -s` as a legal/process assertion by that human, not a formatting convenience;
- configure the submission commit with exactly that human-provided name and email;
- distinguish the raw Git author/committer name and email from GitHub's account association for those fields; a commit resolving to the correct GitHub account does not prove the raw identity matches the DCO trailer;
- before exposing a compare link or recommending submission, inspect the raw commit author and committer directly and verify every `Signed-off-by` trailer, for example with `git show --no-patch --format=fuller HEAD` and `git log -1 --format='%an <%ae>%n%cn <%ce>%n%B'`;
- treat any squash, amend, rebase, cherry-pick, clean-base rebuild, or API commit recreation as a new attribution event that requires the full identity check again;
- do not use a final-commit API or connector that cannot explicitly set the required raw author/committer identity and independently expose or verify the resulting raw metadata; stop at preparation and leave the final DCO commit to ordinary Git or the human;
- if an automated materializer is used for non-final research state, require the contributor identity as explicit input or fixed reviewed configuration and disable the materializer once the submission branch exists;
- if an attribution mistake occurs, stop submission work, create a corrected commit from the clean base or repair it with ordinary Git, move live controlled refs away from the bad commit, archive misleading carriers, and record the correction. Do not rewrite legitimate upstream history belonging to the actual person whose identity was mistakenly copied.

## Incidents that established this rule

### 2026-08-07 — unrelated contributor copied into materializer

During the Cloud Hypervisor #8046 fieldwork, the clean-commit materializer was based on canonical commit `ae04fa80b2e0e52b7a9f4b3fd4239698df586673`, a legitimate upstream commit authored by `leo03164 <leo03164@gmail.com>`. The materializer incorrectly hardcoded that unrelated contributor's identity into `git config` and then used `git commit -s`, causing several fork-only generated commits to be falsely attributed and signed off as that person.

The human submission identity was corrected to:

`Leo Li <cheerleaderleo@outlook.com>`

See `notes/processes/2026-08-07-submission-commit-materializer-postmortem.md`.

### 2026-08-10 — API squash preserved SoB text but not DCO identity proof

Later in the same Cloud Hypervisor pull request, a maintainer requested that a tiny review follow-up be squashed into the original commit. The owned-fork squash was recreated through a GitHub commit API path that preserved the correct `Signed-off-by: Leo Li <cheerleaderleo@outlook.com>` text.

GitHub also associated both author and committer with the `teamleaderleo` account. That provider-level association was incorrectly treated as sufficient identity verification.

The maintainer subsequently reported that the SoB did not match and requested `git commit -s`.

The human submitter repaired the commit locally, explicitly using `Leo Li <cheerleaderleo@outlook.com>`, and verified the raw Git author, committer, and `Signed-off-by` before force-updating the branch. The bad API-squash head `160a1468edac6a8e396972c8809ad066f0afe789` was replaced by human-repaired head `39d446bcb31ccd2004c9a05bdb474bff85921740` without changing the intended source diff.

See `notes/processes/2026-08-10-dco-squash-api-identity-followup.md`.

## Durable rule

The identity check is complete only when the final commit object itself is checked. The GitHub avatar/account attached to a commit and the text of a `Signed-off-by:` trailer are useful evidence, but neither can substitute for the raw author and committer fields.
