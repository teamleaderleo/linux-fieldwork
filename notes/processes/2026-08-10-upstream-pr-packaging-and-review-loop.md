# Upstream PR packaging and review loop — lessons from Cloud Hypervisor ACPI submission

Date: 2026-08-10

## Why this note exists

A technically good candidate can still improve materially during packaging. The useful lesson from the ACPI submission was not “polish forever”; it was learning what kind of scrutiny is worth doing before public review and what kind becomes churn.

The central distinction is:

```text
internal workbench
    ↓
maximize understanding + evidence

upstream submission
    ↓
minimize reviewer effort without hiding limits
```

The same facts do not need the same presentation on both surfaces.

## 1. Freeze product bytes before prose churn

Once a candidate has a defensible product boundary, give it an exact identity before spending time rewriting commit/PR prose.

Useful receipt:

```text
canonical parent
changed files
insertions/deletions
product diff SHA-256
```

Then keep validation-only machinery on a separate branch or commit layer.

This lets review say:

```text
wording changed
validation expanded
workflow changed
        ↓
product bytes did not
```

That is much easier to reason about than repeatedly rebuilding patches from stored layers or letting test-harness commits become indistinguishable from the submitted product.

## 2. Test the exact product commit

A strong validation carrier can sit above the product commit but should:

1. verify the product parent and expected changed files;
2. verify the exact product diff digest;
3. detach/check out the product commit;
4. run formatting, tests, lint, architecture/backend builds there;
5. retain a receipt artifact.

The important property is:

```text
reviewed bytes
    = submitted bytes
    = tested bytes
```

Avoid a validation system that reconstructs source in a way that could silently diverge from the commit humans will review.

## 3. Independent review should challenge the boundary, not just syntax

The most valuable late review on the ACPI patch was not a typo. It asked why three mutex poison errors were being converted when the rest of the VMM uses `lock().unwrap()`.

That exposed a neighboring policy question.

The decision rule that emerged:

```text
change directly required by bounded bug
    ↓
keep

change that silently establishes broader subsystem policy
    ↓
justify explicitly or remove
```

Removing the poison handling made the patch smaller and easier to explain without giving up the core fix.

A good reviewer tries to find the hidden second question that a patch accidentally introduces.

## 4. Rank review feedback by consequence

Not all review comments deserve another product SHA.

A practical ranking:

```text
factual error
    > design/scope ambiguity
    > missing validation surface
    > evidence overclaim
    > prose clarity
    > stylistic preference
```

Examples from the ACPI loop:

- **Factual:** implying fw_cfg `add_acpi()` previously panicked was wrong; its `io::Error` already propagated. Fix the PR prose.
- **Scope:** special poison handling introduced a local mutex policy. Change the product.
- **Validation:** RISC-V was a required CI dependency and missing from the focused matrix. Expand validation without changing product bytes.
- **Style:** “ACPI fixes this structure at 40 bytes” versus “ACPI requires…” is below the threshold once product bytes are frozen.

## 5. Use a stop rule

Without a stop rule, independent reviewers and language models can generate infinite plausible nits.

A useful stop condition:

```text
exact product bytes green
+ relevant architecture/backend surfaces covered
+ independent review converged on design
+ PR factual claims are accurate
+ evidence ceiling is explicit
        ↓
stop proactive product changes
```

After that, source changes should be driven by a real maintainer request, attributable CI failure, upstream source movement, or a concrete counterexample.

“Could be phrased slightly better” is no longer enough to rewrite the commit.

## 6. Commit messages and PR bodies have different jobs

### Commit message

The commit is durable source history. It should explain **why and how**, carry required trailers, and follow repository commit formatting rules such as line wrapping.

Prefer:

```text
problem / why
    ↓
implementation / how
    ↓
issue + attribution + sign-off trailers
```

Do not iterate canonical issue references through a long series of pushed temporary commits. Add `Fixes #...` to the final frozen submission commit.

### PR body

The PR is a web review surface. It does not need artificial 72-column wrapping unless the project explicitly requires it.

Its job is fast orientation:

```text
what was wrong?
what changed?
where does control/error flow go?
what was actually validated?
what was not tested?
```

Normal Markdown paragraphs are easier to edit and read than commit-style hard wrapping.

## 7. “Grug map” first, proof underneath

Small arrow diagrams can carry real explanatory load.

Example shape:

```text
operation
    ↓
subsystem error
    ↓
caller wrapper
    ↓
request returns Err
```

Use real function/type/error names when possible. The diagram should replace prose, not duplicate a paragraph immediately above it.

For an internal investigation, use two layers:

```text
first screen
    ↓
WTF happens? / causal map

later sections
    ↓
source archaeology / exact receipts / caveats / discarded variants
```

This helps both an expert maintainer scanning quickly and a future learner reconstructing the work.

## 8. Simpler language is often more precise

Do not use specialist vocabulary solely because it is technically available.

“Several operations use `unwrap()` / `expect()`” may be better than “several operations are fallible” when the source-level fact is what matters.

Likewise:

```text
I added next_table_address()
```

can be clearer than:

```text
A helper was introduced to centralize...
```

First person is fine in a PR when it sounds natural. The archived commit can remain impersonal if that is the project's style.

## 9. Explicitly state the evidence ceiling

A validation section is more credible when it says what did **not** happen.

Example:

```text
focused unit behavior executed
format/lint/build matrix passed
VM boot smoke test not run
```

Do not let “validated” imply runtime coverage that only exists as compilation.

A negative sentence can increase trust in every positive sentence around it.

## 10. Backlink hygiene must start before packaging

GitHub issue/PR/commit references in interaction surfaces can create third-party timeline noise.

For internal GitHub issue/PR/comment/review text, use:

```text
https://redirect.github.com/OWNER/REPO/issues/N
https://redirect.github.com/OWNER/REPO/pull/N
https://redirect.github.com/OWNER/REPO/commit/SHA
```

Avoid bare `OWNER/REPO#N` and direct canonical issue URLs in interaction prose.

Most importantly, temporary iterative commit messages should avoid canonical issue references entirely. A repeated `Fixes #N` across force-pushed or superseded commits defeats the point of quiet research.

A clean lifecycle is:

```text
internal iteration commits
    ↓
no canonical reference

final frozen upstream commit
    ↓
Fixes #N once

upstream PR
    ↓
intentional issue relationship
```

Repository Markdown files are suitable for deep technical links and historical context, but consistent use of redirect links also makes intent obvious when text is later copied into an interaction surface.

## 11. Public-facing prose has different stakes

Internal research can be verbose because its purpose includes teaching, recovery, and proving every claim.

Public upstream prose has another audience: maintainers already know the repository and want to identify the behavioral change and review risk quickly.

The useful kind of overthinking is therefore **targeted**:

```text
not: can this sentence be polished forever?

but: what does this reviewer need to decide?
```

Condense toward that decision.

The internal record remains the place for the longer explanation a contributor may need in order to defend every line later.

## 12. Preserve discarded designs when they teach something

Do not keep obsolete code in the final patch, but do retain why it was discarded when that reason is reusable.

In the ACPI case, poison handling was removed not because it was syntactically bad or impossible, but because it made a narrow bugfix answer a broader VMM error-policy question.

That distinction is valuable for future work:

```text
technically defensible
    ≠
right scope for this patch
```

## Compact checklist for next time

Before upstream submission:

- identify the exact canonical base;
- freeze the intended product diff and digest;
- separate product from validation-only commits;
- test the exact product commit;
- compare the focused matrix to required upstream CI surfaces;
- get at least one adversarial review of the scope boundary;
- fix factual claims before style claims;
- write the commit once the product is stable;
- keep temporary commit messages free of canonical references;
- make the PR concise, normal Markdown, and explicit about evidence limits;
- use redirect links in internal interaction surfaces;
- stop when remaining feedback is preference rather than decision-changing evidence.
