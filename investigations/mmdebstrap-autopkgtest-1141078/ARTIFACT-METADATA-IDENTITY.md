# Exact GitHub artifact metadata identity for the Packet B receipt

## TL;DR

PR #371 downloads one retained Packet B artifact by source workflow run and artifact name, then interprets its repository checkout, statuses, console ordering, and focused-case result.

The predecessor receipt carried an expected artifact ID and digest, but those values were only command-line metadata copied into the derived JSON. The workflow did not prove that GitHub's server metadata for the downloaded artifact matched the claimed ID, name, source run, digest, and unexpired state.

This focused repair verifies the exact artifact through GitHub's read-only Actions API before download, retains both raw and normalized metadata receipts, and cross-checks the derived Packet B summary against the verified identity.

## Explain like I'm five

The evidence box had a handwritten label saying which sealed package it came from. The reader checked everything inside the box, but never compared that handwritten label with the warehouse record.

The repair asks the warehouse for the package record first. It checks the package number, name, shipment, seal fingerprint, and expiry. Only then does it open and interpret the box.

## Why care

A strong console classifier is still reading the wrong evidence if the selected artifact identity is wrong.

Downloading by run and name establishes a useful selection path, and GitHub's artifact action validates download integrity against server metadata. It does not by itself prove that the server-side artifact selected by those coordinates has the exact ID and digest written in this repository's receipt.

The tracked claim therefore needs two separate contracts:

1. **server metadata identity** — exact ID, name, source workflow run, digest, and unexpired state;
2. **downloaded-content identity** — the action's transport validation plus the artifact's retained repository/status/content receipts.

## Exact source artifact

Expected immutable source artifact:

- repository: `teamleaderleo/linux-fieldwork`;
- workflow run ID: `30641621084`;
- run attempt: `1`;
- artifact ID: `8799126060`;
- artifact name: `mmdebstrap-reproduction-gha-30641621084-1`;
- server digest: `sha256:33f972dfd71c08263a0d766d9e1ded96c11407f001315a2a0c23ae9d2bf68474`;
- expected expired state: `false`.

The content receipt separately requires:

- head `fe49686c333aea3c5b8e378e655c52fa57e9224c`;
- base `c2b7c43a4b6ce883f6dcdbef8d489bcf48323266`;
- generated merge checkout `37648c5efd9cf80b5ae4ec063e8d6cb5b4f82d6e`;
- ordered parents `[base, head]`;
- source run ID and attempt agreement;
- script/container status agreement.

## Metadata verification path

The dedicated workflow uses read-only permissions:

```text
actions: read
contents: read
```

Before downloading content, it calls the exact artifact-ID endpoint:

```text
GET /repos/{owner}/{repo}/actions/artifacts/8799126060
```

The raw response is retained as:

```text
source-artifact-metadata.json
```

`tools/verify_github_artifact_metadata.py` requires:

- metadata is one JSON object;
- `id` is the exact expected positive integer;
- `name` is the exact expected string;
- `workflow_run.id` equals the exact source run;
- `digest` equals the exact expected `sha256:` value;
- `expired` is a boolean and false.

It emits a normalized typed receipt:

```text
source-artifact-metadata-receipt.json
```

Only after this step succeeds does `actions/download-artifact` download the exact run/name artifact.

## Derived-summary cross-check

After the existing Packet B summarizer validates the extracted artifact, the workflow requires:

- derived artifact ID equals verified server ID;
- derived artifact digest equals verified server digest;
- verified artifact name equals the workflow's single `SOURCE_ARTIFACT_NAME` value;
- verified source run equals the workflow's single `SOURCE_RUN_ID` value.

This keeps one expectation source rather than copying the artifact name and run into embedded Python literals.

## Retained evidence

The derived workflow artifact contains:

- raw server metadata JSON;
- normalized metadata receipt;
- metadata verifier stdout;
- existing Packet B typed summary;
- existing summary stdout and bounded decision context.

A later reviewer can therefore distinguish:

- what GitHub reported about the artifact;
- what the verifier accepted;
- what the downloaded content reported about its repository checkout and execution;
- what the Packet B classifier concluded.

## Focused controls

`tests/test_verify_github_artifact_metadata.py` covers:

- exact positive metadata;
- wrong artifact ID;
- wrong artifact name;
- wrong workflow run;
- wrong digest;
- expired artifact;
- missing and wrong-typed fields;
- invalid expected ID and digest;
- workflow ordering: metadata verification before download before interpretation;
- retention of raw and normalized metadata;
- cross-checking derived ID and digest against verified metadata.

## Why the ID endpoint rather than a name-only list

The tracked artifact ID is the narrowest immutable selection coordinate. Verifying its returned name and workflow run proves that the ID belongs to the expected source artifact instead of another artifact in the repository.

The subsequent download remains scoped to the expected source run and name. With immutable v4 artifacts, server metadata verification before download and the action's transport digest validation form complementary checks.

A future workflow that permits mutable artifacts, multiple repositories, replacement by name, or a non-GitHub download path must reopen this design.

## Evidence boundary

This repair establishes GitHub server metadata identity for one retained artifact and its agreement with the derived summary.

It does not:

- recompute a ZIP digest from a stable raw archive URL inside the workflow;
- preserve the source artifact beyond its GitHub retention period;
- prove current-main or literal-head package behavior;
- rerun apt, autopkgtest, Docker, root operations, or package installation;
- alter the canonical log classifier or Packet B product evidence;
- authorize external contact.

The raw metadata and downloaded artifact remain subject to GitHub's service and retention model. If the artifact expires, verification fails closed.

## Carrier boundary

This successor stacks on PR #371 current head `ea40747fe5c192a2afdea663aedf2b0aa21d3969`.

Direct changes:

- `.github/workflows/mmdebstrap-autopkgtest-artifact-receipt.yml`;
- `tools/verify_github_artifact_metadata.py`;
- `tests/test_verify_github_artifact_metadata.py`;
- this record.

No product source, retained package patch, sid package job, downloaded source artifact, canonical log-classifier implementation, or external project changes.

## Disposition

`ARTIFACT METADATA IDENTITY REPAIR` until exact-head repository CI and the dedicated read-only artifact receipt workflow pass and retain the raw plus normalized metadata receipts.

Internal Linux Fieldwork evidence only. No Debian, mmdebstrap upstream, external issue, email, release, deployment, or other public contact is included or authorized.
