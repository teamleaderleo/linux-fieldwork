# systemd bind-path whitespace overlap review

State: `ACTIVE OVERLAP REVIEW — PARSER MATRIX GREEN; SERIALIZATION ROUNDTRIP QUEUED`  
Canonical issue: `systemd/systemd#43214`  
Active implementation: `systemd/systemd#43217`  
External contact authorized: `false`  
External contact made: `none`

## Grammar and ownership boundary

`systemd.exec` documents each whitespace-separated tuple as:

```text
source[:destination[:rbind|norbind]]
```

The option cannot be supplied while destination is omitted. `source::norbind` is therefore a negative control, not compatibility syntax.

The correct parser has two levels:

1. coalesced shell-like whitespace between complete tuples;
2. non-coalesced colon fields inside one tuple.

Because canonical PR #43217 already owns the product change, this is an internal review/execution lane rather than a competing patch.

## Exact active source

```text
canonical base: 63e35ca3f99566095c84248e9eb41a3a6b32f2eb
active PR head: d32993d1f67ec1b42719c89eeda9425042df57ce
active canonical PR: systemd/systemd#43217
```

The PR changes parser logic, execution-context serialization/deserialization, and associated tests.

## Completed parser comparison

Initial run `30759715925` was carrier-owned failure: Meson received a build path without the source path and neither product configured. Its artifacts are retained but support no product conclusion.

The bounded repair completed as Linux Fieldwork run `30795425735`:

```text
canonical base
  job: 91627787064
  artifact: 8849252039
  digest: sha256:cfeb0a0eb01f74caa5d95d364717264715d36e91720619de17b358f020b4764d

active PR
  job: 91627787134
  artifact: 8851890190
  digest: sha256:2588659118757e774e59df61117ab7933f5f86a26224497ca35e463e2f750141
```

Both exact source states configured and built `systemd-analyze`. The corrected grammar matrix showed:

- canonical base emits empty-path warnings for repeated spaces, mixed tabs/spaces, and continuation indentation;
- active PR accepts those forms like ordinary one-space syntax;
- quoted spaces and escaped colons remain accepted;
- source-only, source/destination, options, ignore-missing, and reset controls remain on expected paths;
- invalid options remain rejected;
- omitted destination with option remains malformed;
- too many fields receive the more precise `Too many parameters in BindPaths=` diagnostic.

This supports the active parser repair over the tested documented grammar. It does not establish serializer safety.

## Current source-native serialization gate

```text
controlled repository: teamleaderleo/systemd
branch: fieldwork/43217-bind-serialize-roundtrip
head: cfce4b094043ae4491d8c4632202dad15bd6dfbb
internal draft PR: teamleaderleo/systemd#8
focused run: 30851469604 — queued at last check
jobs:
  canonical base: 91812245943 — queued
  active PR: 91812246010 — queued
```

The controlled branch commits two carrier files and no systemd product source. The workflow checks out exact canonical base and PR head, then injects one source-native core test into the disposable product tree.

The test constructs eight ordered bind mounts covering:

- writable and read-only;
- `rbind` and `norbind`;
- ignore-missing;
- spaces;
- literal colons;
- quotes;
- backslashes;
- tabs;
- embedded newlines;
- identical source and destination.

For each source state it:

1. serializes a complete invocation to an in-memory stream;
2. deserializes into a fresh `ExecContext`;
3. compares source, destination, read-only, recursive, and ignore-missing for every mount;
4. serializes the restored context again;
5. requires byte-identical serialized output;
6. executes under Valgrind;
7. retains exact wire text, source patch, build logs, source blobs, and binary digest.

Static review confirmed `shell_escape()` C-escapes control characters independently of its explicit separator set; tabs and newlines remain in the runtime matrix because the format is record-delimited.

Carrier self-review repairs already retained:

- removed an invalid empty-stderr gate;
- added the required fd utility header;
- added `git add -N` so the injected untracked C file participates in the exact two-file product fence;
- corrected the test from six to eight mounts after adding control characters.

## Decision boundary

Read run `30851469604` by first failing step. If both source states pass, compare the wire forms and determine whether the PR is a compatible canonicalization. If only one fails, isolate the first mismatched field or escaping shape. Do not infer serialization correctness from the parser result.

Current canonical main is ahead of the PR base and the PR is reported non-mergeable. Relevant product files were not directly changed in the observed drift, but shared parsing/namespace helpers moved; a current-main integration rerun remains required after this focused test proves itself.

## Publication boundary

No canonical systemd issue comment, pull request, review, reaction, email, or maintainer contact is authorized or made.
