# Exact receipt for a retained mmdebstrap sid artifact

## TL;DR

The Debian sid package run `30641621084` finished with status 6 and retained a 36-file artifact. The wrapper log proves that the artifact came from the expected generated pull-request merge, but it does not expose the artifact's package console.

This unit downloads that exact retained artifact, verifies its typed repository checkout receipt, runs the existing first-failure classifier over `autopkgtest-console.log`, and reports whether `root-without-cap-sys-admin` completed before the first later failure.

It does not rerun the package matrix or change product code.

## Explain like I'm five

The long exam already put its detailed answers in a sealed box. The outside label says “failed,” but not which answer was wrong.

This receipt opens the exact box, confirms whose exam it was, and reads the first red answer. It does not make the student take the exam again.

## Why care

Packet B's focused hook-free scheduler can be valid even if a later unrelated Debian sid package case fails. Conversely, a broad run that never reaches the capability case does not validate it.

A container status such as 6 cannot distinguish:

- focused case passed, later broad case failed;
- focused case failed;
- focused case never ran;
- artifact belongs to a different repository checkout.

The receipt makes those outcomes machine-readable.

## Exact source boundary

Source workflow run:

- run: `30641621084`;
- attempt: `1`;
- repository head: `fe49686c333aea3c5b8e378e655c52fa57e9224c`;
- generated merge checkout: `37648c5bda3f406ce706b4a5be46c1ccaa354f9c`;
- ordered merge parents: base `c2b7c43a4b6ce883f6dcdbef8d489bcf48323266`, head `fe49686c333aea3c5b8e378e655c52fa57e9224c`;
- artifact ID: `8799126060`;
- artifact name: `mmdebstrap-reproduction-gha-30641621084-1`;
- artifact digest: `sha256:33f972dfd71c08263a0d766d9e1ded96c11407f001315a2a0c23ae9d2bf68474`;
- artifact files: 36;
- source job duration: about 50 minutes;
- wrapper result: status 6, failure.

The raw artifact remains the authority for package evidence. This derived receipt names its source identity rather than replacing it.

## Candidate surfaces

Owning issue: #370.

Branch: `investigation/mmdebstrap-autopkgtest-artifact-receipt`.

Changed surfaces:

- `tools/summarize_mmdebstrap_reproduction.py`;
- `tests/test_summarize_mmdebstrap_reproduction.py`;
- `.github/workflows/mmdebstrap-autopkgtest-artifact-receipt.yml`;
- this record.

The branch starts from current `main` at `c81d665e0acf9523e7f0d20247a8172a2a6648a3`.

## Artifact layout contract

The summarizer recursively locates each required file by exact basename and rejects zero or multiple matches:

- `repository-identity-input.json`;
- `repository-identity.json`;
- `repository-rev-list.txt`;
- `autopkgtest-console.log`;
- `exit-status`;
- `container-exit-status`;
- `result.md`;
- `phase-order.stdout`.

Required paths must be regular, nonsymlink files. Ambiguous layout fails before interpretation.

## Repository identity contract

The retained identity input is passed through the existing canonical classifier:

`tools/audit_pr_evidence_identity.py`

The rebuilt typed receipt must byte-for-byte agree after JSON normalization with the retained output receipt.

Required source identity:

- classification: `synthetic-merge-ref`;
- checkout SHA: `37648c5b...`;
- head SHA: `fe49686c...`;
- base SHA: `c2b7c43a...`;
- ordered parents: `[base, head]`;
- run ID: `30641621084`;
- run attempt: `1`.

The raw `rev-list` line must match the same checkout and ordered parents. An identity mismatch is an artifact-authority failure, not a package result.

## Status contract

`exit-status` and `container-exit-status` must both be nonnegative decimal integers and must agree.

`result.md` must retain:

- that exact status;
- `synthetic-merge-ref` checkout classification.

A package nonzero status remains data. It does not make the receipt tool itself fail.

## First-failure contract

The receipt reuses:

`tools/mmdebstrap_autopkgtest_log.py`

That classifier preserves the first meaningful event in transcript order across:

- mirror failure;
- coverage preflight;
- named coverage case;
- wrapper-only failure;
- pass.

The derived JSON retains:

- classifier output;
- first failed and last named test;
- named test count;
- console SHA-256 and line count;
- bounded context around the first failure;
- a short console tail.

## Focused Packet B case contract

The receipt independently records every named occurrence of:

`root-without-cap-sys-admin`

Each occurrence retains:

- line;
- index/total;
- dimensions;
- result outcome and outcome line.

Focus state is one of:

- `absent`;
- `passed`;
- `failed`;
- `unresolved`.

Two order booleans answer the Packet B decision:

- did the focus case begin before the first meaningful failure?
- did it complete successfully before the first meaningful failure?

The phase-order transformation receipt is retained verbatim alongside this result.

## Focused synthetic controls

`tests/test_summarize_mmdebstrap_reproduction.py` covers:

1. focus case passes, later broad case fails;
2. focus case itself fails;
3. focus case absent;
4. repository head mismatch;
5. duplicate required artifact basename;
6. script/container status disagreement.

The positive fixture uses a real typed identity input/output pair built with the canonical classifier.

## Hosted receipt workflow

The dedicated workflow has read-only permissions:

- `contents: read`;
- `actions: read`.

It downloads only artifact name `mmdebstrap-reproduction-gha-30641621084-1` from exact run `30641621084`, creates the typed summary, prints the decision fields and bounded failure context, and uploads only the derived JSON/stdout receipt.

No package, container, mirror, root, mount, or network-package transaction is rerun. The only network action is GitHub downloading its own retained artifact.

## Why this approach

### Why not rerun the package matrix?

The source artifact already exists and has an exact digest. A rerun would consume about an hour, produce a different base/merge/environment identity, and still not interpret the prior evidence.

### Why not trust wrapper status 6?

The wrapper does not expose the first named failure or focused-case execution.

### Why not parse only the final lines?

Later wrapper failures can overwrite the useful owner. The canonical classifier preserves the first meaningful event.

### Why not copy the artifact into the repository?

The raw artifact is 707 KiB compressed and already has a GitHub retention/digest identity. The repository should retain the compact, typed conclusion and source coordinates, not duplicate every raw file.

## Evidence boundary

This unit establishes interpretation of one exact retained artifact.

It does not prove:

- literal-head execution;
- current-main freshness;
- package behavior outside this run;
- source applicability;
- a product fix;
- Debian autopkgtest infrastructure generally;
- upstream acceptance.

The raw artifact expires on 2026-08-14 unless separately retained. The derived receipt preserves the decision-changing fields and raw artifact digest, not the complete console bytes.

## Stop rule

Stop after exact-head repository and dedicated receipt workflows pass and the real receipt classifies:

- repository identity;
- script/container status;
- first meaningful failure;
- focused case state and ordering.

Any product or broad-matrix repair should then use the named first failure as its owner.

## Disposition

`HOLD` until the dedicated receipt workflow executes against artifact `8799126060` and the exact repository gate passes.

The next disposition depends on the observed focus state:

- focus passed before later failure: preserve Packet B integration evidence and route the later broad failure separately;
- focus failed: repair Packet B or product behavior;
- focus absent/unresolved: repair carrier ordering or execution;
- identity/layout mismatch: repair evidence authority.

## Authority

Internal Linux Fieldwork evidence only. No Debian, mmdebstrap upstream, external issue, email, release, deployment, or other public contact is included or authorized.
