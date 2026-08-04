# Handoff: coreutils install just-created ownership

## State

`ACCEPT SOURCE — direct source-only confirmation pending; public contact unauthorized`

## Exact identities

- Historical canonical base: `uutils/coreutils@b13ee7a8319f439cb9a1ba550e98de665f9c4bb1`
- Canonical main at overlap refresh: `uutils/coreutils@21d4e9635b07a04f262cd8a5386f2987bca6cfef`
- Controlled repository: `teamleaderleo/coreutils`
- Controlled branch: `fieldwork/install-refuse-just-created-overwrite-12926`
- Accepted source-only head: `b6f6e76138b27fd7a221a551aa6261752d513f19`
- Controlled source PR: `teamleaderleo/coreutils#1`
- Linux Fieldwork branch: `investigate/coreutils-install-just-created-12926`
- Linux Fieldwork PR: `teamleaderleo/linux-fieldwork#430`

## Final source fence

Exactly four files differ from the historical base:

- `src/uu/install/src/install.rs`
- `src/uu/install/locales/en-US.ftl`
- `src/uu/install/locales/fr-FR.ftl`
- `tests/by-util/test_install.rs`

Temporary execution files are absent:

- `.fieldwork/refine-install-12926.patch`
- `.github/workflows/fieldwork-refine-install-12926.yml`

## Accepted candidate boundary

- compare no-op: does not reserve
- source metadata failure: does not reserve
- source read or incomplete copy failure: does not reserve
- successful `copy_file()`: reserve before finalization
- post-copy failure leaving destination: keep reservation
- strip failure removing destination: release reservation
- only explicit numbered mode permits repeated destination

The implementation keeps one copy pipeline and invokes an ownership callback only after completed data copy.

## Executed gates

### Independent staged-head gate

Linux Fieldwork run `30849357346`, job `91805346376`: success.

Passed:

- exact controlled checkout;
- zero-fuzz candidate application;
- repository rustfmt;
- eight focused ownership tests;
- complete `install` test module;
- focused clippy;
- exact candidate diff recording.

### Promotion

Controlled commit `b6f6e761...` contains the tested formatted source and test bytes, required English/French diagnostics, and removal of the temporary patch/workflow.

### Direct source-only gate

The current Linux Fieldwork verifier checks out `b6f6e761...` directly and requires:

- exact four-file fence;
- no temporary execution files;
- rustfmt check;
- all eight focused tests;
- complete `install` module;
- focused clippy;
- exact identity, diff hygiene, and clean tree.

This direct run and Linux Fieldwork CI are the only remaining gates before composing PR #430.

## Review

Controlled source review `4856820032`: `ACCEPT — technically ready for owner/human review`.

Source PR #1 is non-draft. No requested reviewers or canonical interaction are claimed.

## Current-main overlap

The 32-commit range from historical base to canonical main `21d4e963...` changes no `install` source, locale, or `test_install.rs` path.

No overlap currently invalidates the candidate. Restack onto current public main and rerun immediately before any authorized canonical filing.

## Adjacent finding

Backup rollback after data-copy failure remains a separate operation owner:

- controlled source PR `teamleaderleo/coreutils#3`
- Linux Fieldwork PR `teamleaderleo/linux-fieldwork#431`

Do not widen the destination-ownership patch to restore backups.

## Durable evidence

- `README.md` — accepted design, execution, review, limits, and transition
- `GNU_BEHAVIOR_RECEIPT.md` — GNU 9.7 behavior matrix and fixtures
- `.github/workflows/verify-coreutils-install-12926.yml` — direct exact-source verifier
- controlled source PR #1 — final source-only diff and review receipt

## First incomplete step

Inspect the direct source-only verifier triggered by the current Linux Fieldwork head.

If green:

1. update PR #430 with run and job IDs;
2. mark it ready;
3. merge the durable Linux Fieldwork record;
4. leave controlled source PR #1 open for human review.

If red:

1. classify the first failing exact source, format, test, module, lint, identity, or hygiene step;
2. repair only that owner;
3. keep the GNU behavior matrix and source boundary unchanged unless product evidence requires a source change.

## Authority

Canonical-upstream contact: `false`.

No upstream issue, pull request, comment, review, email, reaction, release, deployment, or patch submission was authorized or made.
