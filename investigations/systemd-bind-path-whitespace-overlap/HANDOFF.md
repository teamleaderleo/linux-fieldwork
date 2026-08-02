# Handoff — systemd bind-path whitespace overlap

Handoff date: 2026-08-02  
State: `ACTIVE — BASE/PR SOURCE COMPARISON QUEUED`  
External contact authorized: `false`  
External contact made: `none`

## Exact stopping point

```text
canonical issue: systemd/systemd#43214
active canonical PR: systemd/systemd#43217
canonical base: 63e35ca3f99566095c84248e9eb41a3a6b32f2eb
active PR head: d32993d1f67ec1b42719c89eeda9425042df57ce
controlled product branch: none
Linux Fieldwork workflow: .github/workflows/systemd-bind-path-source-compare.yml
first registered run: 30759608071
state at handoff update: queued
```

## Demonstrated mechanism

Repeated whitespace is interpreted through the same no-coalescing separator treatment used for colon fields. Whitespace separates complete bind tuples; colon separates fields inside a tuple. Repeated whitespace must coalesce without changing colon-field parsing.

Installed Debian 13 systemd 257 reproduced empty-path warnings for repeated spaces and line-continuation indentation.

## Corrected grammar finding

The previous handoff incorrectly said empty colon fields were meaningful. `systemd.exec` documents:

```text
source[:destination[:rbind|norbind]]
```

and explicitly requires the option string to be omitted when destination is omitted. Therefore:

```text
source::norbind
```

is an invalid control, not compatibility behavior. The fixture and README have been corrected.

## Durable fixture

```text
investigations/systemd-bind-path-whitespace-overlap/reproduce.sh
```

It now executes valid and invalid cases independently:

- repeated, tab/mixed, and continuation whitespace;
- ordinary one-space syntax;
- source-only, source/destination, and full triples;
- quoted spaces and escaped colons;
- ignore-missing marker;
- reset assignment;
- omitted destination with options;
- too many fields;
- invalid option.

It accepts `SYSTEMD_ANALYZE=/path/to/binary`, retains per-case outputs and hashes, and owns temporary cleanup.

## Controlled comparison

Workflow run `30759608071` builds `systemd-analyze` from:

1. canonical base `63e35ca3...`;
2. active PR head `d32993d...`.

Each row records source file blobs, Meson/build logs, analyzer identity and digest, complete parser-case outputs, and source-native test inventory.

## First incomplete step

Read both jobs from run `30759608071` in order:

1. classify dependency/configure/build failures separately from parser behavior;
2. retain artifact IDs and digests;
3. compare all valid and invalid case diagnostics;
4. verify the PR removes only repeated-whitespace empty-path warnings;
5. verify documented invalid tuples remain rejected or warned;
6. inspect quoting and escaped-colon outputs;
7. then identify and run the narrowest execution-context serialization/deserialization test.

## Review warning

Do not approve the broad active PR from parser output alone. It also changes serialization quoting and deserialization. Those paths require a source-native round-trip gate after the built analyzer comparison.

## Publication boundary

No canonical comment or review is authorized. Retain findings internally until the user explicitly approves public communication.

## Cleanup state

No local systemd checkout or build survives. Hosted jobs use disposable runners and bounded artifacts. No service, mount, namespace, credential, or canonical repository state is changed.
