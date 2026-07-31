# Pull-request checkout identity in Debian sid package evidence

## TL;DR

The current-main Debian sid carrier executes from GitHub Actions' default pull-request checkout: a generated merge commit. Its artifact already retains imported-source, transformed-source, patch, package, command, and result identities, but it did not name the repository checkout that orchestrated those steps.

This repair reuses the repository's typed PR-evidence classifier. The privileged job now records the generated checkout SHA, declared head and base SHAs, event SHA, ordered parents, refs, run identity, classification, raw revision line, and receipt digest inside the package artifact. A reversed or unrelated merge topology fails before product execution.

Owning issue: #364. Stacked source carrier: PR #361.

## Explain like I'm five

The package test reads a temporary book made by putting the proposed page into the current book. The old envelope listed the page contents but not the temporary book it actually read.

The repaired envelope names:

- the temporary book;
- the proposed page;
- the base book;
- the order in which they were combined.

If those identities do not agree, the test stops before claiming a package result.

## Why care

A literal-head run and a generated-merge run answer different questions.

- A head run proves the proposed commit executes by itself.
- A merge-ref run proves the proposed commit integrates with one exact base snapshot.

Base movement can change the generated merge without changing the branch head. A base-side workflow or tool can also supply behavior absent from the branch. Without an in-artifact receipt, later readers can attribute orchestration behavior to the wrong commit.

## Exact boundary

Reviewed predecessor:

- PR #361 branch: `investigation/mmdebstrap-autopkgtest-current-main-v2`;
- predecessor head: `c2b7c43a4b6ce883f6dcdbef8d489bcf48323266`;
- predecessor generated merge observed by GitHub: `8c2c057a9fd2b3bfc09994e009cf7957e0883691`;
- imported source: unchanged;
- product patches: unchanged.

Repair construction branch:

- `repair/361-sid-checkout-identity`;
- created directly from the predecessor head;
- changed surfaces: workflow, reproduction script, focused test, this record.

The general identity vocabulary and validator already live on `main`:

- `tools/audit_pr_evidence_identity.py`;
- `investigations/pr-evidence-identity/README.md`;
- completed issue #342.

## Cross-context review

### 1. Workflow checkout policy

Observed:

- the privileged job used default `actions/checkout@v4`;
- the job therefore exercised the generated pull-request merge;
- the checkout used shallow history insufficient to guarantee both parent identities were locally visible.

Repair:

- use `fetch-depth: 2`;
- record `git rev-list --parents -n 1 HEAD` before entering the container;
- pass declared event/head/base/ref/run identity explicitly.

### 2. Host-to-container transfer

Observed:

- the disposable container received run and timeout identity only;
- the repository commit topology existed on the host checkout and was lost at the container boundary.

Repair:

- pass the raw revision line as one environment value;
- pass event, head, base, refs, run ID, run attempt, and expected classification separately;
- keep the source tree mounted read-only in meaning: no repository commit or ref is changed.

### 3. Classifier and ordered parents

Observed:

- a two-parent commit is not sufficient by itself;
- the expected generated merge requires ordered parents `[base, head]` and checkout SHA equal to the event SHA.

Repair:

- build the existing classifier's typed JSON input;
- require `synthetic-merge-ref` for the pull-request package job;
- retain classifier stdout and stderr;
- reject reversed parents and every other checkout before root/product work.

### 4. Artifact and early preflight

Observed:

- source and patch hashes did not establish the repository checkout;
- an early root or dependency preflight could still finish without a repository identity receipt.

Repair:

- record checkout identity before the root requirement;
- retain the raw line, input JSON, typed receipt or local note, classification, and receipt digest;
- include classification and digest in both early and final result summaries;
- include the typed receipt in the human-readable provenance.

## Candidate contract

For a pull-request package job:

1. every required event field is nonempty;
2. the raw checkout line parses into one checkout SHA plus ordered parents;
3. the existing classifier validates exact types and lowercase 40-hex SHAs;
4. classification must equal `synthetic-merge-ref`;
5. typed input, output, raw line, stdout, stderr, classification, and digest remain in the artifact;
6. identity failure exits 2 before root, patch, mirror, or package execution.

For local or workflow-dispatch use:

- record `not-a-pull-request` and the available raw revision line;
- do not manufacture a pull-request classification;
- continue to the existing root and dependency preflight.

## Focused controls

`tests/test_mmdebstrap_sid_checkout_identity.py` covers:

- workflow fetch depth and exact environment transfer;
- expected generated merge `checkout == event`, parents `[base, head]`;
- typed receipt retained before the deliberate non-root neutral exit;
- classification and digest visible in `result.md`;
- reversed parents rejected as `other-checkout` before the root check;
- classifier input and diagnostic retained on failure;
- local execution recorded as `not-a-pull-request` without a false PR receipt.

Every executable control uses a temporary run directory and a fake `id` command. No root, package, mirror, network, mount, or container operation is required by the focused matrix.

## Why this approach

Adding a second custom classifier would create vocabulary drift. Recording only `GITHUB_SHA` would not prove parent order or declared head/base identity. Recording only the branch head would mislabel the generated merge as literal-head execution.

The existing classifier is the smallest reusable owner. Passing the host's raw `rev-list` line avoids requiring Git history inside the disposable container while preserving the exact checkout observation.

## Alternatives considered

### Explicit literal-head checkout for the package job

This would prove head execution but would stop proving integration with the current base-side workflow and tools. It is a separate useful gate, not a replacement for the current package integration job.

### Infer identity from artifact file hashes

File hashes prove selected content, not commit topology or workflow provenance. Distinct commits can contain the same files.

### Trust the GitHub run association

A later reader should not need an API reconstruction to know what the downloaded artifact exercised. The artifact should be self-describing.

## Evidence boundary

This repair establishes repository checkout identity only.

It does not prove:

- literal-head execution;
- source applicability or zero-fuzz patch semantics;
- package correctness;
- current-main freshness after base movement;
- mergeability;
- complete sid execution;
- upstream acceptance.

The generated-merge receipt expires when either declared head or base changes. The real sid matrix remains authoritative only for the exact generated checkout named in its own artifact.

## Stop rule

Stop this unit after:

- the expected generated merge is retained;
- reversed parent order fails before product work;
- local execution remains accurately non-PR;
- exact-head repository CI and the privileged sid artifact carry the new receipt.

Literal-head package execution or broader workflow identity policy belongs to a distinct carrier if it changes a later decision.

## Disposition

`REPAIR` until the stacked repository gate and activated privileged sid job execute on the final exact head. A green artifact with `synthetic-merge-ref` should move this evidence repair to `MERGE LOCALLY` as part of the canonical integration carrier.

## Authority

Internal Linux Fieldwork metadata and disposable package evidence only. No Debian, mmdebstrap upstream, external issue, email, release, deployment, or other public contact is included or authorized.
