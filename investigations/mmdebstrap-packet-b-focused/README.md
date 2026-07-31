# Current-main focused Packet B capability execution

State: `candidate — exact-head sid execution pending`

## TL;DR

Run only the exact hook-free producer/consumer pair needed by Packet B:

```text
create-directory
root-without-cap-sys-admin
```

The package testsuite performs its real mirror and autopkgtest setup, executes the installed `/usr/bin/mmdebstrap`, preserves hard failures, and exits immediately after the capability consumer. Broad coverage cannot fail first, replace the result, or make the focus appear only in a skipped inventory.

## Explain like I'm five

A prior full exam stopped before the question we cared about. This carrier gives the student the prerequisite question, then the capability question, records both grades, and ends the exam before unrelated questions can interfere.

## Why care

Packet B already has exact predecessor evidence that the focused pair passed, but a later current-main broad artifact never completed the focus case. A current-main decision needs an execution surface that guarantees the case either passes, fails, or times out visibly.

## Evidence history

### Valid focused predecessor

Run `30636627420` / 974 on head `fe84899d7c4de599038c41ad13810b82f832baf6` recorded:

```text
(30/284) create-directory                 SUCCESS
(41/284) root-without-cap-sys-admin       SUCCESS
```

Artifact `8796132761`, digest `sha256:8e0ab36d6938c5eb676cd8f1550dec978743c3e12d4da4c6b862602c5f407227`.

The later broad failure was a phase-scoped fixture mismatch, not a focused product failure.

### Later unresolved broad artifact

Merged receipt PR #376 authenticated run `30641621084` and established that `root-without-cap-sys-admin` appeared only in the skipped inventory after broad `(242/284) chrootless` failed. That artifact proves neither focus pass nor focus failure.

### Focused run 11 — identity gate stopped before privilege

Exact head `6540437cc0350752e3229824d5836beb980604d6` passed repository CI `30655286527` / 1055. Focused workflow `30655286545` / 11 then stopped in the generated-merge identity step before privileged Docker or package execution.

The checkout was generated merge `abb9c45adad4f3ba97b222b76914bc628dd28403`, whose observed first parent was `e4e28e2e7606c1dde7dfe706205c961e5c37060d` and second parent was the exact PR head. The pull-request event payload still exposed older base SHA `1ac6aadf884ca69935c2f763b9788476a313645c`. The workflow incorrectly used that advisory event field as the authoritative merge parent and the identity auditor returned status 2.

Artifact `8803277230`, digest `sha256:4762326e9af4a56eb9900fc197ab67057139a483b4583276f2179f592bdf90c3`, retains the four pre-execution identity files. No package result, focus outcome, timeout, or product failure exists for this run.

The repair derives `base_sha` from the checkout's observed first parent, retains the event base separately as `event_base_sha`, and still requires exact event SHA, exact second-parent head SHA, ordered parents, and `synthetic-merge-ref` classification. A source contract forbids returning to event-base authority.

## Candidate construction

The disposable source copy receives two exact retained changes:

1. the current-main hook-free hard-failure scheduling patch;
2. a formatted proxy whose behavioral calls reach installed `/usr/bin/mmdebstrap`.

`tools/prepare_mmdebstrap_packet_b_focused.py` then:

- requires the unprepared order `broad < hook-free hard < soft transition`;
- verifies the exact metadata selector, producer/consumer list, hook-free command, hard-failure exit, and timeout policy;
- moves the hook-free block ahead of broad coverage;
- inserts one explicit `exit 0` after that block;
- requires final order `hook-free hard < focused stop < broad < soft transition`;
- writes a digest and ordering receipt.

Both patches must apply with zero fuzz and zero offset. Imported source is copied and never modified in place.

## Result verification

`tools/verify_mmdebstrap_packet_b_focused.py` accepts only a console with:

- raw autopkgtest status 0;
- exactly two named tests in the complete console;
- exactly one `create-directory` occurrence with `SUCCESS`;
- exactly one `root-without-cap-sys-admin` occurrence with `SUCCESS`;
- completed producer before completed consumer;
- exactly one final `testsuite PASS` and no `testsuite FAIL`.

Missing, extra, duplicated, unresolved, reversed, failed, unrelated-before, or broad-after cases fail closed.

## Status policy

- exact focused success plus receipt: 0;
- outer timeout status 124: neutral 77;
- bare 137 remains a hard failure because it can represent an external or OOM SIGKILL rather than an owned timeout;
- every other nonzero autopkgtest status is preserved as a hard failure;
- raw success with receipt disagreement: 2.

The workflow requires carrier and container status agreement before promotion. Focused controls execute the status table, including `124→77` and `137→137`.

## Safety, execution authority, and cleanup

The privileged workflow job is eligible only when all three conditions are true before checkout:

- event is `pull_request`;
- the head repository exactly equals the owning repository;
- the head branch is exactly `packet-b-focused-current-main`.

This prevents fork-controlled or unrelated branch code from reaching the proposed checkout and `docker run --privileged` surface. A source-shape control retains that guard and the single privileged launch.

The runner:

- validates the exact temporary runtime with the shared strict runtime guard;
- rejects repository or HOME overlap, roots, symlink leaves, and unsafe parents;
- clears EXIT re-entry and keeps handled INT/TERM ignored during bounded cleanup;
- retains primary status over cleanup status;
- stores result evidence only below this investigation's validated run directory;
- runs package work inside a disposable privileged Debian sid container;
- leaves imported source unchanged.

## Generated-merge identity

Before privileged work, the workflow records:

- checked-out commit;
- ordered parents;
- exact head SHA from the event;
- base SHA from the observed first parent;
- event-provided base SHA as advisory provenance only;
- event SHA and refs;
- run ID and attempt;
- typed `synthetic-merge-ref` classification and digest.

A topology, head, or event-SHA mismatch fails before package execution. Base-branch movement between event creation and execution remains visible without being misclassified as the generated merge's parent.

## Candidate fence

- `.github/workflows/mmdebstrap-packet-b-focused.yml`;
- this README;
- `0001-use-installed-mmdebstrap-proxy.patch`;
- `scripts/run_mmdebstrap_packet_b_focused.sh`;
- `tools/prepare_mmdebstrap_packet_b_focused.py`;
- `tools/verify_mmdebstrap_packet_b_focused.py`;
- `tests/test_mmdebstrap_packet_b_focused_harness.py`;
- `tests/test_prepare_mmdebstrap_packet_b_focused.py`;
- `tests/test_verify_mmdebstrap_packet_b_focused.py`.

## Required gates

- complete repository CI;
- focused preparation, verifier, status-precedence, runner, optimizer-safe receipt, workflow-authority, and merge-parent controls;
- exact generated-merge identity;
- disposable sid package execution;
- exact producer and consumer success receipt;
- no other named case;
- artifact upload, cleanup, and source-diff confirmation;
- complete nine-file review on the unchanged head.

## Disposition

**EXECUTE.** If the exact current-head sid workflow records both successes and no other named case, Packet B may advance from current-main integration hold. Any hard failure remains authoritative and must be classified before changing product code.

## Evidence boundary and authority

This carrier proves one Debian sid producer/capability pair against the imported source generation and installed package selected by autopkgtest. It does not establish broad-suite success, other distributions, upstream acceptance, or sandboxing.

Internal Linux Fieldwork work only. No Debian or mmdebstrap upstream issue, email, patch, merge request, release, deployment, or public contact is authorized or included.

Refs #75, #153, #194, run 974, merged PR #376, and historical PRs #72/#361/#366.
