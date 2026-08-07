# Contributor identity guardrail

Contributor identity is not inferred metadata.

For any commit intended for upstream submission:

- never copy `user.name`, `user.email`, author, committer, or `Signed-off-by` identity from the base commit, a nearby upstream commit, a repository owner, or a GitHub username;
- obtain the contributor name and email explicitly from the human who will submit the contribution;
- treat `git commit -s` as a legal/process assertion by that human, not a formatting convenience;
- configure the submission commit with exactly that human-provided name and email;
- before exposing a compare link or recommending submission, fetch the final commit from GitHub and verify the resolved author/committer identity and every `Signed-off-by` trailer;
- if an automated materializer is used, require the contributor identity as explicit input or fixed reviewed configuration and disable the materializer once the submission branch exists;
- if an attribution mistake occurs, stop submission work, create a corrected commit from the clean base, move live controlled refs away from the bad commit, archive misleading carriers, and record the correction. Do not rewrite legitimate upstream history belonging to the actual person whose identity was mistakenly copied.

## Incident that established this rule

During the Cloud Hypervisor #8046 fieldwork, the clean-commit materializer was based on canonical commit `ae04fa80b2e0e52b7a9f4b3fd4239698df586673`, a legitimate upstream commit authored by `leo03164 <leo03164@gmail.com>`. The materializer incorrectly hardcoded that unrelated contributor's identity into `git config` and then used `git commit -s`, causing several fork-only generated commits to be falsely attributed and signed off as that person.

The human submission identity was later corrected to:

`Leo Li <cheerleaderleo@outlook.com>`

The submitted Cloud Hypervisor PR uses the corrected commit. Historical GitHub cross-reference events from the discarded fork commits may remain visible, but no active submission branch should point to them.
