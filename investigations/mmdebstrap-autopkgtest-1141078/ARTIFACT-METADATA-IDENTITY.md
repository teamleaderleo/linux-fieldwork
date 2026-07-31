# Exact GitHub artifact metadata identity for the Packet B receipt

## TL;DR

Merged PR #376 downloads one retained Packet B artifact and interprets its checkout, statuses, console ordering, and focused-case result.

The landed receipt carries an expected artifact ID and digest, but those values are command-line metadata copied into the derived JSON. It does not prove that GitHub's server metadata for the downloaded artifact matches the claimed ID, name, source run, digest, and unexpired state.

This current-main repair verifies the exact artifact through GitHub's read-only Actions API, downloads that same verified artifact ID, retains raw and normalized metadata, and cross-checks the derived Packet B summary against that verified identity.

## Explain like I'm five

The evidence box had a handwritten label saying which sealed package it came from. The reader checked everything inside, but never compared the label with the warehouse record.

The repair asks the warehouse first. It checks the package number, name, shipment, seal fingerprint, and expiry, then opens that exact package number instead of looking up the package by label again.

## Why care

A strong console classifier is still reading the wrong evidence if artifact identity is wrong.

A name-based download after ID verification creates a second selection boundary. The tracked claim needs two complementary contracts:

1. **server metadata identity** — exact ID, name, source run, digest, and unexpired state;
2. **downloaded-content identity** — download by that exact verified ID, transport validation, and the artifact's retained checkout, status, and console receipts.

## Exact source artifact

- source workflow run: `30641621084`;
- attempt: `1`;
- artifact ID: `8799126060`;
- name: `mmdebstrap-reproduction-gha-30641621084-1`;
- digest: `sha256:33f972dfd71c08263a0d766d9e1ded96c11407f001315a2a0c23ae9d2bf68474`;
- expected expired state: `false`.

The existing content receipt separately requires:

- head `fe49686c333aea3c5b8e378e655c52fa57e9224c`;
- base `c2b7c43a4b6ce883f6dcdbef8d489bcf48323266`;
- generated merge checkout `37648c5efd9cf80b5ae4ec063e8d6cb5b4f82d6e`;
- ordered parents `[base, head]`;
- source run and attempt agreement;
- script/container status agreement.

## Verification path

The dedicated workflow keeps read-only permissions:

```text
actions: read
contents: read
```

Before download it requests the exact artifact-ID endpoint:

```text
GET /repos/{owner}/{repo}/actions/artifacts/8799126060
```

`tools/verify_github_artifact_metadata.py` requires:

- one JSON object;
- exact positive integer `id`;
- exact `name`;
- exact `workflow_run.id`;
- exact `sha256:` digest;
- boolean `expired=false`.

It retains:

- `source-artifact-metadata.json` — raw server response;
- `source-artifact-metadata-receipt.json` — normalized accepted identity;
- verifier stdout.

Only then does `actions/download-artifact@v4` fetch `artifact-ids: 8799126060`. The source run remains an explicit scope and is also verified through `workflow_run.id`; the artifact name remains an identity field, not a second selector.

After content interpretation, the workflow requires the derived summary's ID and digest to equal the verified server receipt. It also compares verified name and source run with the workflow's single environment constants rather than duplicating literals in embedded Python.

## Controls

`tests/test_verify_github_artifact_metadata.py` covers:

- exact positive metadata;
- wrong ID, name, source run, or digest;
- expired artifact;
- missing and wrong-typed fields;
- invalid expected ID/digest;
- metadata verification before download before interpretation;
- exact `artifact-ids` download;
- retention of raw and normalized metadata;
- derived ID/digest cross-checks.

## Why use the ID endpoint and ID download

The tracked artifact ID is the narrowest immutable selection coordinate. Verifying its returned name and workflow run proves the ID belongs to the expected source artifact.

The subsequent download consumes that same ID. For immutable v4 artifacts, exact-ID metadata verification, exact-ID download, and the action's transport digest validation are complementary.

Reopen this design for mutable artifacts, another repository, a non-GitHub download path, or a future action contract that does not preserve exact artifact-ID selection.

## Landing history

The neutral receipt landed through PR #376 as `ef834ce38e40539bd4f8a62ba79ea767c899004a`.

The first current-main repair, PR #379 head `27e07b792eb752a0159021924b50040cad2afe1f`, passed:

- Linux Fieldwork CI `30651839596` / 1027;
- dedicated read-only receipt workflow `30651839763` / 12.

During its gate, main moved by the disjoint APT classifier repair landed as `1ac6aadf884ca69935c2f763b9788476a313645c`. The generated merge had no fresh workflow receipt. This v2 carrier recreates the same verified metadata/download blobs directly on that newer main generation instead of treating disjointness as execution evidence.

## Four-file boundary

- `.github/workflows/mmdebstrap-autopkgtest-artifact-receipt.yml`;
- `tools/verify_github_artifact_metadata.py`;
- `tests/test_verify_github_artifact_metadata.py`;
- this record.

No product source, package patch, sid package job, canonical log classifier, summarizer behavior, or downloaded source artifact changes.

## Evidence boundary

This establishes GitHub server metadata identity for one retained artifact, exact-ID download selection, and agreement with the derived summary.

It does not extend retention, rerun package tests, prove current-main package behavior, or recompute a stable raw ZIP digest independently of GitHub's artifact service. Expired metadata fails closed.

## Disposition

`CURRENT-MAIN ARTIFACT METADATA AND DOWNLOAD IDENTITY REPAIR` until fresh exact-head repository CI and the dedicated read-only receipt workflow pass and retain both metadata layers. Then merge locally and verify the landed workflow directly.

Internal Linux Fieldwork evidence only. No external contact is authorized or included.
