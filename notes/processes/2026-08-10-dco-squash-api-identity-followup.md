# DCO squash identity follow-up — 2026-08-10

Companion to:

- `notes/processes/2026-08-07-submission-commit-materializer-postmortem.md`
- `CONTRIBUTOR_IDENTITY.md`
- `SOURCE_BRANCH_HYGIENE.md`

Canonical issue:  
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8046

Upstream pull request:  
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8699

## In simple words

The Cloud Hypervisor fix itself was fine and had already been approved. A later squash recreated the one-commit branch through a GitHub API commit-writing path. The new commit kept the correct `Signed-off-by:` text and GitHub associated its author/committer with the correct account, but the underlying Git author identity did not satisfy the maintainer's DCO check.

The maintainer reported: the SoB did not match; use `git commit -s`.

The human submitter repaired the commit locally with explicit Git name/email, verified the raw author and committer using ordinary Git, and force-updated the existing branch. No source line changed during that repair.

The lesson is narrower than the earlier materializer incident but important for a phone-first workflow: **GitHub account identity is not the same thing as raw Git commit identity.**

## Exact sequence

The original submitted commit was:

```text
f7e386b074138700cb57101b8c3ef0ecc069a018
```

A review follow-up removed four comments, after which the maintainer requested a squash.

The automated owned-fork squash produced:

```text
160a1468edac6a8e396972c8809ad066f0afe789
```

The final source tree and commit message were correct, including:

```text
Signed-off-by: Leo Li <cheerleaderleo@outlook.com>
```

The GitHub connector also resolved both author and committer to:

```text
teamleaderleo
```

That was incorrectly accepted as proof that DCO identity matched.

After the maintainer flagged the mismatch, the human submitter used local Git with:

```text
user.name  = Leo Li
user.email = cheerleaderleo@outlook.com
```

and amended/reset the author identity. Before pushing, the human verified:

```text
Author:    Leo Li <cheerleaderleo@outlook.com>
Commit:    Leo Li <cheerleaderleo@outlook.com>
Signed-off-by: Leo Li <cheerleaderleo@outlook.com>
```

The repaired branch head is:

```text
39d446bcb31ccd2004c9a05bdb474bff85921740
```

It remains one commit with the same intended source diff.

## The identity layers

A contribution commit has at least three identity surfaces that must not be conflated:

```text
Git commit object
├── author name + email
├── committer name + email
└── commit message
    └── Signed-off-by: name + email

GitHub presentation
└── account associated with author/committer email
```

GitHub can show the same account for two commits whose raw name/email fields differ. A provider-level account match therefore cannot prove a DCO match.

For DCO, the raw commit fields and the certification trailer must be checked directly.

## What was wrong with the squash path

The available low-level GitHub commit-creation action accepted the parent, tree, and message but did not expose an explicit author/committer identity.

That limitation should have been a stop condition for a final DCO-bearing history rewrite.

Instead, the commit was created and then validated using the information the provider happened to expose. The check answered:

```text
Does GitHub associate this commit with teamleaderleo?
```

but the required question was:

```text
Does the raw Git author/committer identity match
Leo Li <cheerleaderleo@outlook.com>, and does the SoB certify the same identity?
```

Those are different assertions.

## Correct verification

For an upstream-intended DCO commit, run a raw Git check before the push:

```sh
git show --no-patch --format=fuller HEAD
git log -1 --format='%an <%ae>%n%cn <%ce>%n%B'
```

Require the intended identity in all applicable places.

For this contributor that means:

```text
Author:       Leo Li <cheerleaderleo@outlook.com>
Committer:    Leo Li <cheerleaderleo@outlook.com>
Signed-off-by: Leo Li <cheerleaderleo@outlook.com>
```

GitHub account resolution is useful secondary evidence only.

## Rule for tooling

A tool may create the final DCO-bearing commit only when it can:

1. explicitly set the intended raw author and committer identity; and
2. independently expose or verify the resulting raw commit metadata.

If either capability is absent, the tool stops at preparation:

```text
prepare tree / patch / tests / branch
                |
                v
human runs normal Git commit/amend
                |
                v
raw metadata verification
                |
                v
push --force-with-lease when history changed
```

Do not compensate for missing identity controls by hand-constructing only the `Signed-off-by:` trailer.

## History rewrites reopen identity review

Repeat the full identity check after any operation that creates a new commit object:

- squash;
- amend;
- rebase;
- cherry-pick;
- commit recreation through an API;
- rebuilding from a clean base.

Even if the source tree and message are byte-for-byte equivalent, the SHA and attribution metadata can change.

## Why this matters to the phone-first workflow

The phone-first model still works well for most of the loop:

- issue and source research;
- candidate editing in owned forks;
- tests and CI;
- review analysis;
- small source follow-ups;
- Fieldwork records and evidence.

The missing reliable primitive is final human-attributed commit creation and rewrite. Until the automation surface supports raw author/committer control and verification, final DCO commits should be signed or repaired with ordinary Git by the human.

That is deliberately a boring boundary. The answer is not another commit materializer.

## Outcome

- Source behavior did not regress.
- Maintainer approval of the code preceded the DCO metadata comment.
- The bad API-squash head `160a1468...` was replaced.
- The repaired head `39d446b...` was created with explicit human Git identity.
- Raw author, committer, and sign-off were checked locally before push.
- The `Assisted-by:` trailer remained unchanged because it was unrelated to the DCO mismatch.

## Reusable lesson

**Verify the commit object, not the avatar.**

A matching GitHub account and a matching `Signed-off-by:` string can still leave a DCO mismatch if the underlying commit author identity differs.
