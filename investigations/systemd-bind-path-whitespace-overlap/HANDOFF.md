# Handoff — systemd bind-path whitespace overlap

Handoff date: 2026-08-03  
State: `ACTIVE — PARSER COMPARISON COMPLETE; SERIALIZATION ROUNDTRIP QUEUED`  
External contact authorized: `false`  
External contact made: `none`

## Exact source boundary

```text
canonical issue: systemd/systemd#43214
active canonical PR: systemd/systemd#43217
canonical base: 63e35ca3f99566095c84248e9eb41a3a6b32f2eb
active PR head: d32993d1f67ec1b42719c89eeda9425042df57ce
```

Documented grammar:

```text
source[:destination[:rbind|norbind]]
```

If destination is omitted, the option must also be omitted. `source::norbind` is a negative control, not preserved syntax.

## Superseded harness run

```text
run: 30759715925
canonical job: 91527946682
active PR job: 91527946711
```

Both exact sources were checked out, but neither configured because the workflow omitted the Meson source directory. Retained artifacts:

```text
canonical: 8838880432
  digest: sha256:65b940618c63baefaf6dde22a95febb2f47ce6cea5d6ddef82b0f90417864797
active PR: 8839366457
  digest: sha256:fba8903937e894d5356c0f88eb4a7551f2372f2e49f19d557d46c0ba2a331155
```

No product result is taken from that run.

## Completed parser comparison

```text
Linux Fieldwork run: 30795425735
carrier branch: repair/systemd-bind-path-source-compare
carrier head: ad93e4a627b3ba96ebc770c04819a8fb5e1ab808
```

Canonical base:

```text
job: 91627787064
conclusion: success
artifact: 8849252039
digest: sha256:cfeb0a0eb01f74caa5d95d364717264715d36e91720619de17b358f020b4764d
```

Active PR:

```text
job: 91627787134
conclusion: success
artifact: 8851890190
digest: sha256:2588659118757e774e59df61117ab7933f5f86a26224497ca35e463e2f750141
```

Both rows passed carrier contract, exact checkout, dependency setup, Meson configuration, focused `systemd-analyze` build, corrected grammar matrix, source-native inventory, and artifact upload.

Classification:

- canonical base warns on empty paths created by continued indentation, repeated spaces, and mixed tab/space separators;
- active PR accepts those forms cleanly;
- ordinary one-space syntax remains clean;
- quoted spaces and escaped colons remain accepted;
- source-only, source/destination, full options, ignore-missing, and reset controls remain on their expected paths;
- invalid options remain rejected;
- omitted destination with option remains invalid;
- too many fields receive a specific `Too many parameters in BindPaths=` diagnostic.

This supports active PR #43217 for the tested parser grammar. It does not establish serialization safety.

## Current serialization carrier

```text
controlled repository: teamleaderleo/systemd
branch: fieldwork/43217-bind-serialize-roundtrip
head: d137ab24b2fc4b5371a804e38a1b5e67fc251ace
internal draft PR: teamleaderleo/systemd#8
workflow: Fieldwork bind mount serialization roundtrip
run: 30849764916
state at handoff: queued
```

The branch commits two test-infrastructure files and no product source. The workflow checks out both exact source states and injects a source-native core test into the disposable tree.

The test creates six ordered bind mounts covering:

```text
writable/read-only
rbind/norbind
ignore-missing
spaces
literal colons
quotes
backslashes
identical source/destination
```

For each variant it:

1. serializes a complete invocation to an in-memory stream;
2. deserializes into a fresh context;
3. compares source, destination, read-only, recursive, and ignore-missing for every mount;
4. serializes the restored context again;
5. requires byte-identical output;
6. executes under Valgrind;
7. retains serialized stdout, stderr, source patch, build logs, source blobs, and binary digest.

Self-review removed an invalid empty-stderr gate. systemd's test framework may emit diagnostics on successful runs; exit status, exact field comparison, deterministic reserialization, and Valgrind are the gates.

Other fork workflows registered on the same head include Build test, Unit tests, CIFuzz, ClusterFuzzLite, mkosi, lint, and differential ShellCheck. Do not infer their status without re-querying.

## First incomplete step

Read run `30849764916` in this order:

1. source checkout and two-file carrier fence;
2. Meson injection/target ownership;
3. compile errors in the new core test, if any;
4. first direct round-trip assertion failure;
5. first Valgrind error;
6. compare canonical and PR serialized wire text only after both field round-trips are classified.

Possible interpretations:

- **both pass:** new format is a deterministic compatible canonicalization over tested fields; compare wire changes and proceed to complete PR test review;
- **base fails, PR passes:** identify which escaping shape the PR newly repairs;
- **base passes, PR fails:** isolate first field loss or parser mismatch before approving the broad change;
- **both fail at build:** repair only test-carrier integration, not product assumptions.

## Publication boundary

No canonical systemd comment, review, reaction, email, or pull request is authorized. Retain results internally.

## Cleanup state

All source changes and builds are confined to disposable hosted runners. No service, mount, namespace, device, credential, or canonical repository state is changed.
