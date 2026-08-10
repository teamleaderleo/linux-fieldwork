# ACPI submission process notes

Date: 2026-08-10

This file keeps investigation-specific workflow lessons. The reusable version lives at `notes/processes/2026-08-10-upstream-pr-packaging-and-review-loop.md`.

## Submission evolution

```text
broad internal candidate
    ↓
validated
    ↓
independent review questions scope
    ↓
remove poisoned-lock policy
    ↓
freeze smaller product
    ↓
validate exact bytes
    ↓
independent review finds RISC-V gap
    ↓
expand validation only
    ↓
write final commit once
    ↓
open/iterate PR prose
    ↓
ready for review
```

The important observation is that the largest improvement after the first green result came from **scope review**, not from another implementation idea.

## Audience split

The internal record is partly for learning and partly for future defense of the patch. It can explain `unwrap`, `Result`, `Ok`, `?`, why hex addresses appear in the test, why static size checks moved to compile time, and why a discarded mutex design was plausible.

The public PR is for maintainers who already know Rust and Cloud Hypervisor. It should not make them excavate the simple change from a tutorial.

This tension is useful rather than problematic:

```text
internal audience includes contributor-learning
upstream audience prioritizes maintainer decision speed
```

Write both surfaces for their actual audience instead of forcing one document to satisfy both.

## Wording churn that was worth it

The PR opening went through several forms. The final version says some ACPI operations use `unwrap()` / `expect()` and can panic rather than claiming every relevant failure was previously a panic. That matters because fw_cfg `add_acpi()` already returned `io::Error`; the patch moves that existing error under `acpi::Error`.

The final text also replaced abstract wording with source-level wording where possible. `fallible` was correct, but naming `unwrap()` / `expect()` was simpler and more immediately tied to the diff.

The arrow diagram survived several reviews because it explains both ownership and the otherwise mechanical `?` churn quickly.

## Wording churn that was not worth changing product for

After the final source bytes were frozen, reviewers still preferred small alternatives such as:

- `ACPI requires this SRAT structure...` versus `ACPI fixes this SRAT structure...`;
- `their results are currently unwrapped` versus `their failure cases are currently unwrapped` in the commit message.

Those are reasonable preferences but not enough to create a new final commit SHA, re-sign, force-push, and generate another canonical reference event.

The threshold changed once packaging became canonical.

## Backlink hygiene failure mode

Early internal issues/commits used direct canonical references. During later packaging it became obvious that iterative pushed commit messages containing `Fixes #...` can create repeated upstream timeline references even if the commits are later replaced.

For this investigation the final rule became:

```text
iterative/internal commits -> no canonical issue reference
internal interaction links  -> redirect.github.com
final upstream commit       -> Fixes #8666 once
upstream PR                 -> intentional Fixes #8666 relationship
```

The historical churn cannot be undone cleanly; the useful response is to improve the convention rather than repeatedly editing old interaction history.

## Product/validation separation

The first internal runner reconstructed stored patch layers. The final v2 validation carrier instead verified the frozen product diff and detached to the product commit before running tests/builds.

That model is preferable for submission candidates because there is no extra reconstruction step between review bytes and tested bytes.

## Human scrutiny is part of the process

The final PR wording benefited from slow, word-by-word human review. The useful goal was not maximum polish; it was making every public sentence something the contributor could understand and defend.

A productive framing is:

```text
overthink with a target
    ↓
what does the maintainer need to decide?
what can I defend if asked?
what evidence do I actually have?
```

That is different from endless aesthetic editing.

## Current stop condition

Upstream PR https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8709 is ready for review at head `e9c86bacee14a2fd6fe871dc678c6b3f1ac4012a`.

Do not proactively alter product bytes for further stylistic preferences. Respond to actual maintainer review, upstream CI, source movement, or a concrete new counterexample.
