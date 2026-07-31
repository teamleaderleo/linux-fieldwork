# Deep dive

## Question and observed failure

State the bounded question, exact baseline behavior, and why the result belongs to this source owner rather than a harness, packaging, environment, or evidence defect.

## Source mechanism

Walk through the relevant implementation path. Link exact files, symbols, tests, and prior carriers through `SOURCE_MAP.md`.

## Reproduction narrative

Explain the smallest distinguishing fixture and the baseline/candidate outcomes. Keep full commands and receipts in `TESTS.md`.

## Approach history

### Approach A — name

- mechanism;
- evidence gathered;
- result;
- compatibility cost;
- accepted, rejected, superseded, or still open.

### Approach B — name

- mechanism;
- evidence gathered;
- result;
- compatibility cost;
- accepted, rejected, superseded, or still open.

Add sections for every approach that changed the decision. Preserve failed approaches when they rule out an attractive but incorrect fix.

## Selected correction

Describe the selected implementation and why it is the smallest coherent upstream unit.

## Why the changes belong together

Explain shared ownership, ordering, overlapping source lines, invariant, or test matrix. If they do not belong together, record the split in `DECISIONS.md`.

## Compatibility analysis

Cover the properties affected by the mechanism, not only the headline output:

- bytes and logical content;
- status, signal, stderr, and continuation;
- files, modes, ownership, timestamps, links, and metadata;
- process, descriptor, socket, mount, lock, and cleanup state;
- environment and command lookup;
- cache visibility, framing, retry, and publication;
- supported platforms, versions, modes, and tool variants.

Delete irrelevant categories rather than leaving generic claims.

## Negative controls and losing mutations

Record how the tests prove the detector can lose and cannot classify every run as success.

## Current upstream and historical review

Record related upstream discussion, prior patches, design precedent, and any active overlap. Distinguish source fact from inference.

## Remaining questions

For each open question, name the exact discriminator. Do not leave broad “needs more testing” language.

## Evidence boundary

State what has and has not been demonstrated, including platform, privilege, fixture, implementation, integration, and lifecycle limits.

## Reopen triggers

List concrete source, identity, compatibility, result, or authority changes that would justify reopening a settled decision.
