# Maintainer-facing communication

## In simple words

Linux Fieldwork should know more than it says publicly.

An investigation may need exact source identities, environment details, fixture history, competing candidates, failure classification, artifact digests, broad matrices, cleanup receipts, and discarded designs. A maintainer-facing issue, pull request, or reply usually needs a much smaller surface: the concrete problem, the project contract that makes it wrong or disputed, the smallest proposed change, and the evidence that distinguishes that change.

Do not turn a rich investigation into a thin investigation. Derive a decision-sized maintainer packet from it.

## Write for the next decision

Before drafting maintainer-facing text, ask what the maintainer actually needs to decide next.

Usually make these facts recoverable quickly:

```text
observable problem or concrete question
target contract or compatibility assumption
smallest repair or proposed contract change
distinguishing reproduction or regression
important nearby behavior that is intentionally unchanged
```

Once those are clear, stop unless the target repository's template asks for more.

Exact heads, CI run IDs, artifact digests, carrier history, internal state names, discarded variants, and coordination details stay in Linux Fieldwork unless they directly affect the maintainer's decision.

## Investigation voice and maintainer voice are different

A strong internal carrier can be long. That is often correct.

For example, a Linux Fieldwork investigation may need to prove:

- which process or component owns the transition;
- the exact baseline and candidate source;
- which privilege or architecture ran;
- whether a hosted failure belongs to the product or harness;
- whether cleanup and rerun succeeded;
- which adjacent variants lost and why.

The maintainer-facing form should normally compress that into the mechanism and boundary.

Do not copy a whole investigation README into an upstream issue or pull request. Do not delete the investigation detail merely to make the internal record look like an upstream PR.

## Identify the target contract before calling something a bug

A Linux or systems project may intentionally preserve behavior for ABI, compatibility, historical, performance, backend, distribution, or implementation-parity reasons even when a broader specification or abstract design principle suggests a different behavior.

Before presenting a defect claim, separate:

```text
external specification or kernel/API contract
project documentation and tests
historical compatibility behavior
maintainer-stated policy
observed implementation
remaining disagreement
```

Then classify the proposal:

- **implementation repair** — current behavior violates the project's intended contract;
- **contract clarification** — project code, tests, docs, or history disagree about the intended behavior;
- **contract change** — the proposal asks the project to revise an intentional assumption.

A green candidate proves what the patch does. It does not prove that maintainers want the contract the patch implements.

## Make narrowing easy

Reviewer feedback is new evidence.

If a maintainer identifies a stronger local contract or a smaller valid repair boundary, update the thesis, scope, and tests. Do not preserve a broader proposal just because more work has already been invested in it.

A useful reply shape is:

> You're right about X. I was optimizing for Y, but this project preserves Z. I've narrowed the patch to A; B stays separate.

This is not a ritual apology. It records which premise changed and what the candidate now claims.

Cloud Hypervisor's ACPI error work is a good internal model: the first candidate also propagated poisoned mutexes, but the final contribution removed that local policy because the wider VMM did not share it. The narrower patch was easier to defend because it followed the target's existing error boundary instead of inventing a new one.

## Use issues and pull requests for different jobs

A useful issue usually establishes the problem or contract question:

```text
minimal reproduction
actual behavior
expected or disputed behavior
practical consequence
scope boundary
```

A useful pull request usually establishes the proposed implementation:

```text
smallest change
why that owner is the right boundary
important non-goal
regression or validation
target-required checklist or metadata
```

Do not make a maintainer reconstruct the bug from the diff. Do not duplicate every investigation transcript in the pull request either.

## Tone

Prefer a tone that is calm, specific, collaborative, and technically confident.

- Use concrete nouns and verbs instead of sales language such as "robust", "comprehensive", or "production-ready".
- State demonstrated facts plainly.
- Mark real uncertainty where it exists instead of hedging every sentence.
- Own a mistaken premise without groveling.
- Do not perform expertise; show it through the reproduction, source model, patch, and test.
- Do not narrate every branch rewrite, queued job, temporary carrier, or internal handoff in a public thread.
- Edit first when possible instead of posting stream-of-consciousness correction messages.
- A short "thanks" is fine when natural, but substantive feedback that changes the patch deserves a substantive reply.

The goal is not maximum formality. The goal is low-friction technical cooperation.

## Keep the proof behind the claim

A short public explanation is only trustworthy when the internal evidence remains strong.

For every maintainer-facing claim, Linux Fieldwork should still be able to recover:

- the exact source generation;
- the distinguishing baseline/candidate evidence;
- negative controls;
- environment and privilege boundary;
- relevant compatibility checks;
- cleanup and rerun status;
- known limits and reopen triggers.

Compression is presentation, not evidence deletion.

## Good internal examples

Recent Linux Fieldwork work illustrates the distinction:

- **Bubblewrap helper-zombie investigation:** the internal carrier preserves privileged-container evidence, exit-status controls, background-child behavior, and capability limits. A maintainer packet can reduce that to the eventfd ownership race, the live-descendant discriminator, the narrow drain-before-notify change, and the regression.
- **runc sd_notify READY ordering:** the internal execution carrier names exact source, historical context, real Unix-datagram behavior, and a five-part gate. A maintainer-facing patch can simply show that READY detection checks the whole datagram instead of the current field, then provide READY-first / READY-second / no-READY regressions.
- **Tini startup races:** the scout correctly keeps process-group forwarding and parent-death setup as two findings. They should remain separate maintainer conversations unless one target change genuinely owns both.
- **Cloud Hypervisor ACPI errors:** narrowing away the mutex-poison policy improved the contribution because it aligned the patch with the target's established error architecture.

These are examples, not templates. Target repository conventions always win.

## Contribution history

Track substantive contribution separately from landing mechanics.

A target may squash, cherry-pick, relocate tests, remove reproduction-only files, rewrite a small implementation detail, or use a maintainer-managed landing branch. Those actions do not by themselves establish that the contribution was independently replaced.

Record author or co-author metadata plainly when it exists. When only material incorporation is evident, describe the implementation, tests, reproduction, or design boundary that carried forward without inventing ownership percentages.

Use terms such as `superseded` for obsolete artifacts only when the surrounding wording cannot be mistaken for a claim that the underlying contribution disappeared.

## Final check before a human submits

Ask:

```text
Can a maintainer see the next decision in under a minute?
Does the draft identify the target's actual contract?
Is the repair smaller than the investigation that discovered it?
Did later feedback change the thesis without changing the top-level draft?
Is any internal process detail competing with the technical point?
Are issue and pull-request responsibilities separated cleanly?
Is contribution history described accurately without downplaying or inflating it?
Are all target-required templates, sign-offs, disclosures, and metadata preserved?
```

If the answer is no, refine the packet before asking a human to publish it.

## Upstream boundary

This document changes communication preparation only. It grants no authority to open or edit an external issue, pull request, review, comment, email, patch submission, merge, release, or deployment. Follow `AGENTS.md`, `ADAPTIVE_COORDINATION.md`, and the current human authorization for every upstream interaction.
