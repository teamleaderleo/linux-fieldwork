# Handoff: coreutils install just-created ownership

## State

`REVIEW` — candidate staged; executable gates queued; no green refinement receipt yet.

## Exact identities

- Canonical source base: `uutils/coreutils@b13ee7a8319f439cb9a1ba550e98de665f9c4bb1`
- Canonical main at last refresh: `a73055191b6d8f144c96bd487c90ae270f30c7a3`
- Controlled repository: `teamleaderleo/coreutils`
- Controlled branch: `fieldwork/install-refuse-just-created-overwrite-12926`
- Controlled staged head: `8b41c8e08dcb7db59da348279ed4cfb58efc4282`
- Controlled draft PR: `teamleaderleo/coreutils#1`
- Linux Fieldwork branch: `investigate/coreutils-install-just-created-12926`
- Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#430`

## Current gates

- Fork verifier run: `30798087273`
  - job: `91636144880`
  - last observed state: `queued`
- Latest independent Linux Fieldwork verifier run: `30798591945`
  - job: `91637726645`
  - last observed state: `queued`
- Earlier refinement run: `30759417796`
  - job: `91527159381`
  - result: failed before compilation because the staged patch had corrupt unified-diff hunk counts
  - classification: fieldwork packaging failure, not product behavior
- Original focused run: `30752473403`
  - job: `91508843610`
  - result: passed patch application, formatting, ordinary refusal, simple-backup preservation, and explicit numbered-backup exception

Do not claim the eight-case refinement suite, full install test module, or clippy passed until one current gate completes green.

## Current candidate boundary

- compare no-op: does not reserve
- source stat failure: does not reserve
- source read/copy failure: does not reserve
- `copy_file()` completes: reserve before finalization
- post-copy failure leaving destination: keep reservation
- strip failure removing destination: release reservation
- only explicit numbered mode permits repeated destination

The staged implementation keeps one copy pipeline and adds `copy_with_created_callback()`. A previous duplicated-pipeline version was rejected during self-review.

## Focused tests staged

1. ordinary repeated-destination refusal
2. preservation of original simple backup
3. explicit numbered-backup exception
4. compare no-op does not reserve
5. missing source does not reserve
6. `/proc/self/mem` read error does not reserve
7. post-copy chown failure keeps reservation
8. strip failure removes and releases destination

## Durable evidence

- `README.md` — current design, source boundary, results, limits
- `GNU_BEHAVIOR_RECEIPT.md` — GNU 9.7 behavior matrix and fixtures
- `.github/workflows/verify-coreutils-install-12926.yml` — independent read-only verifier

## Review state

At last refresh:

- `teamleaderleo/coreutils#1`: no comments, no submitted reviews, no requested reviewers
- `teamleaderleo/linux-fieldwork#430`: no comments, no submitted reviews

Upstream PR `uutils/coreutils#12063` is the relevant integration pressure. Its review history requested idiomatic platform APIs, formatting, and clippy. No comment or review was posted there.

## Adjacent finding split out

Backup rollback after `copy_file()` failure is a separate operation owner. It is tracked in:

- controlled source draft `teamleaderleo/coreutils#3`
- Linux Fieldwork draft `teamleaderleo/linux-fieldwork#431`

Do not widen this ownership patch to perform backup rollback.

## First incomplete step

Inspect the first current verifier to leave `queued` state.

If it fails:

1. fetch job steps and logs;
2. classify the first distinguishing failure as workflow, transformer/patch, fixture, compile, test, or lint;
3. repair that owner only;
4. rerun unchanged downstream checks.

If it passes and the push-side promotion runs:

1. refresh the controlled branch head;
2. confirm `.fieldwork/refine-install-12926.patch` and `.github/workflows/fieldwork-refine-install-12926.yml` were removed;
3. confirm the final diff contains only intended source, tests, and locale files;
4. compare against current canonical main, not the recorded `a730551…` assumption;
5. inspect every changed file and update README/HANDOFF with exact final blobs and receipts;
6. keep drafts and make no canonical-upstream contact without explicit authorization.

## Authority

Canonical-upstream contact: `false`.

No upstream issue comment, PR, review, email, or patch submission was authorized or made.
