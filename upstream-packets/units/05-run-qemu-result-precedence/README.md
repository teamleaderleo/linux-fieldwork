# Unit 05 — mmdebstrap `run_qemu.sh` result precedence

State: `ACTIVE`  
Priority-zero issue: #397, unit 05  
Worker or variant: `GPT-5.6 Thinking upstream extraction pass`  
Linux Fieldwork branch: `upstream/unit-05-run-qemu-result-precedence`  
External contact authorized: `false`

## TL;DR

The controlled GitHub mirror is now usable as the candidate repository. Its `master` branch is commit `574048f2a720057b75e56622003932f344dc700a`, and repository-root `run_qemu.sh` is exactly Git blob `426aeeb854173569b24e64d6eb85019f45bdf0b6`, byte-identical to the source used by the canonical Linux Fieldwork work.

A four-commit candidate branch now exists at:

```text
repository: teamleaderleo/mmdebstrap
branch: linux-fieldwork/unit-05-run-qemu-result-precedence
head: 457095c6f89655ab12b7055307f519e71bb0dbca
base: 574048f2a720057b75e56622003932f344dc700a
relation: four commits ahead, zero behind
changed files: run_qemu.sh only
final blob: 3e8d4dc07f91d246a372749eb49ff9489c21c7b7
```

The selected result order is:

```text
captured host failure
> completed guest or protocol failure
> first signal received during ordinary cleanup
> first cleanup failure
> success
```

The candidate bytes match the previously validated composed script: 2,924 bytes, SHA-256 `8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f`, and `/bin/sh -n` succeeds.

## Accomplished behavior

`run_qemu.sh` now:

- captures the host command result before cleanup;
- separates ordinary EXIT cleanup from explicit INT and TERM cleanup;
- preserves host failure ahead of guest and cleanup outcomes;
- treats completed guest nonzero, malformed, unreadable, or missing status as failure 1 when no host failure exists;
- retains the first INT or TERM received during ordinary cleanup;
- keeps later handled INT and TERM from replacing an established signal result or interrupting bounded cleanup;
- retains the first cleanup failure while later cleanup actions continue;
- runs cleanup once;
- keeps a completed guest failure ahead of a later cleanup-time signal.

## Why care

The original shared `EXIT INT TERM` handler could overwrite timeout or host failure with generic guest failure, return guest-dependent results for INT or TERM, re-enter cleanup, lose first-signal identity, ignore cancellation during ordinary cleanup, and replace a completed guest failure with a later cleanup event.

Those outcomes misclassify the failure owner and can leave temporary state behind.

## Scope

### Included

- repository-root `run_qemu.sh`;
- result selection and cleanup ownership;
- separate EXIT and explicit-signal handlers;
- first-writer signal retention;
- first cleanup-failure retention;
- four reviewable source commits;
- exact source, blob, compare, and syntax receipts.

### Excluded

- QEMU and `debvm-run` command construction;
- timeout policy;
- process-group delivery or escalation;
- HUP and QUIT policy;
- guest image, network, mount, root, or package-install execution;
- public issue, pull request, merge request, comment, email, or review.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` |
| Intended base branch | `master` |
| Controlled mirror/fork | `https://github.com/teamleaderleo/mmdebstrap` |
| Mirror base commit | `574048f2a720057b75e56622003932f344dc700a` |
| Mirror base `run_qemu.sh` blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` |
| Candidate source branch | `linux-fieldwork/unit-05-run-qemu-result-precedence` |
| Candidate head | `457095c6f89655ab12b7055307f519e71bb0dbca` |
| Candidate final `run_qemu.sh` blob | `3e8d4dc07f91d246a372749eb49ff9489c21c7b7` |
| Candidate SHA-256 | `8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f` |
| Linux Fieldwork branch | `upstream/unit-05-run-qemu-result-precedence` |
| Retained patch series | [`patches/`](patches/) |
| Proposed destination | canonical repository-root `run_qemu.sh` |
| Delivery method | Salsa fork and merge request after explicit authorization |

## Candidate commits

1. `614fb26a4f0724618a5eecd3ce1bee12454ff7de` — preserve the primary result through cleanup.
2. `cb6ef6d6c2b1368b3603b2ec06635c3815f31e11` — retain the first handled signal through cleanup.
3. `13cf34fd87d44b4d37c6767fdbd153b2ef535a57` — retain signals received during ordinary EXIT cleanup.
4. `457095c6f89655ab12b7055307f519e71bb0dbca` — preserve completed guest failure before a later cleanup signal.

The direct compare against mirror `master` is one modified file with 61 additions and 10 deletions.

## Canonical Linux Fieldwork lineage

- owning issue: #269;
- event-order review: #297;
- component carriers: PRs #270, #282, #290, and #304;
- canonical composition: PR #319;
- canonical composition head: `2fe3f99364df29de217536dc35a4d03b10f49640`;
- canonical merge: `b196d6b45f496d8eb2d763922532ad257f24bba8`;
- exact-head CI: run `30628645668`, job 889, success, 276 tests.

## Demonstrated

- The controlled mirror base file is exactly the imported source blob.
- The four packet patches apply in order without errors to that source.
- The final candidate bytes equal the previously validated composed bytes.
- `/bin/sh -n` succeeds on the final candidate.
- The candidate branch is four commits ahead, zero behind, and changes only `run_qemu.sh`.
- The canonical focused suite previously passed on the same source transformation and retains every predecessor negative control.

## Remaining technical gates

1. Search the current canonical Salsa project for equivalent active work when access is available.
2. Confirm the canonical Salsa `master` file remains byte-compatible with mirror base blob `426aeeb…` before any submission.
3. Run current upstream ordinary checks on candidate head `457095c6…`.
4. Run an authorized bounded QEMU/`debvm-run` smoke test only when a disposable environment exists.
5. Refresh the merge-request draft with the final canonical base identity.

The user has no fetch command or repository setup task. The controlled mirror and candidate branch already exist.

## Current disposition

`ACTIVE` — the source candidate is complete on the controlled mirror. Remaining work is canonical-host reconciliation and upstream-native execution.

## Next human decision

After the remaining checks, choose one:

- authorize preparation or submission of a Salsa merge request;
- hold for more testing;
- retire if canonical upstream already contains equivalent work.

## Authority

Internal repository reads, branch creation, commits, tests, packet writing, and issue checkpoints are authorized. External contact remains unauthorized, and none has been made.
