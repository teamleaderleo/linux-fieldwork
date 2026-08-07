# Submission-commit materializer incident — 2026-08-07

This is the Linux Fieldwork companion to the general Fieldwork postmortem at:

`teamleaderleo/fieldwork:research/postmortems/2026-08-07-cloud-hypervisor-submission-materializer.md`

## In simple words

The Cloud Hypervisor #8046 investigation had a good source fix and good runtime evidence, but the packaging machinery became much more complicated than the patch.

A temporary GitHub Actions workflow was allowed to create a fresh signed-off submission commit and force-push it to a clean branch every time the mutable research branch triggered the workflow. Repeated runs therefore created many distinct temporary commits. Because those commits referenced the canonical issue, GitHub recorded many cross-reference events on the upstream issue timeline.

An early version of the workflow also used the Git identity of an unrelated real upstream contributor. `git commit -s` then created temporary fork commits falsely authored and signed off as that contributor.

The final upstream pull request is correctly attributed and was not submitted with the wrong identity.

Canonical issue:  
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8046

Upstream pull request:  
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8699

## Exact local evidence

Representative obsolete wrong-identity commits include:

- `a291aea2806186a85a0feae23e83f839d0b2ecff`
- `260646882274ef07bfba9797a82519ef0cbefcba`

Those commits contained:

```text
Signed-off-by: leo03164 <leo03164@gmail.com>
```

`leo03164` is a real Cloud Hypervisor contributor. Their identity came from legitimate upstream history and should never have been reused for a new contribution.

The corrected final submitted commit is:

```text
f7e386b074138700cb57101b8c3ef0ecc069a018
```

with:

```text
Signed-off-by: Leo Li <cheerleaderleo@outlook.com>
```

GitHub resolves the final commit author and committer to the submitting `teamleaderleo` account.

## The bad workflow pattern

The materializer effectively did:

```text
push to mutable research branch
        |
        v
checkout clean upstream base
        |
        v
apply retained patch
        |
        v
git config user.name / user.email
        |
        v
git commit -s
        |
        v
git push --force clean-submission-branch
```

The workflow had `contents: write`, so its token was intentionally powerful enough to create commits and move branch refs inside the controlled fork.

That ability is not itself a GitHub defect. The bad design decision was attaching human authorship/DCO production to repeatable CI.

## Why there were so many commits

A Git commit is more than its source diff. Creating the same patch again at another time can produce a different SHA because author/committer metadata and timestamps are part of the commit object.

During the investigation, the research branch and workflow were edited repeatedly to change packaging details, base revisions, identity, trailers, comments, and runner behavior. Multiple workflow executions were therefore queued. Each execution could create another distinct commit and force-push it to the clean branch.

The source patch did not change that many times. The **packaging workflow reran that many times**.

## Why there were so many upstream backlinks

The temporary commits carried canonical issue-closing/reference text such as:

```text
Fixes #8046
```

Every newly pushed SHA containing that reference was eligible to appear in the canonical issue timeline. Because the push actor was the workflow token, GitHub grouped those events as `github-actions` adding commits that referenced the issue.

This turned a tiny upstream issue into a visibly noisy timeline even though most of the commits represented the same candidate source transformation.

## Attribution root cause

The materializer once configured:

```text
git config user.name leo03164
git config user.email leo03164@gmail.com
```

and then ran:

```text
git commit -s
```

That copied an unrelated contributor identity into a new commit and caused the DCO trailer to assert their sign-off.

Contributor identity is not build metadata. It is a human attribution and certification boundary.

## Cleanup performed

- Final branch `fix/8046-shutdown-events` points to correctly attributed commit `f7e386b...`.
- Upstream PR #8699 uses that final commit.
- Fork PR #5 was closed as superseded by the upstream PR.
- Fork PR #1 was archived as diagnostic/runtime evidence.
- Fork PR #4 remains clearly marked obsolete due to wrong contributor identity.
- The obsolete `linux-fieldwork/api-shutdown-events-clean` ref was moved to the correctly attributed final commit.
- The submission materializer was archived and no longer has write/force-push behavior.
- `CONTRIBUTOR_IDENTITY.md` records the explicit identity-verification rule.
- Active Fieldwork interaction surfaces now use `redirect.github.com` for quiet external references where applicable.

Historical upstream issue timeline events remain historical records; there is no useful local cleanup that can erase already-recorded canonical events.

## Rules from this incident

1. **Do not use repeatable CI as a human submission-commit factory.**
2. Research may be mutable; the submission commit is created deliberately once.
3. After creation, CI tests the exact submission SHA instead of recreating it.
4. Never infer DCO identity from the base commit, repository owner, nearby author, or old config.
5. Verify final author, committer, `Signed-off-by`, source diff, and assistance trailers before giving the human an upstream compare link.
6. Disposable/internal commits should not contain canonical closing keywords such as `Fixes` or `Closes`.
7. Write-capable temporary scaffolding must be disabled immediately after promotion.
8. If repeatable write automation is genuinely necessary, use stale-run cancellation/concurrency controls and make the write target explicitly non-submission state.

## Better pattern

```text
research branch
    |
    +-- reproduce
    +-- test
    +-- revise
    +-- preserve evidence
    |
    v
human accepts exact candidate
    |
    v
create one correctly attributed submission commit
    |
    v
CI validates that immutable SHA
    |
    v
human submits upstream
```

The general lesson is that automation should prove a contribution artifact, not continually recreate the human attribution statement attached to it.
