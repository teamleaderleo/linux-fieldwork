# systemd bind-path whitespace overlap review

State: `ACTIVE OVERLAP REVIEW — PARSER MATRIX GREEN; SERIALIZATION ROUNDTRIP QUEUED`  
Canonical issue: `systemd/systemd#43214`  
Active implementation: `systemd/systemd#43217`  
External contact authorized: `false`  
External contact made: `none`

## Question

Does active PR #43217 fix repeated whitespace between `BindPaths=` and `BindReadOnlyPaths=` entries while preserving documented tuple grammar, quoting, escaped colons, markers, reset behavior, malformed-input diagnostics, and execution-context serialization/deserialization?

Because an active canonical implementation already owns the source change, this workspace is a review and execution lane, not a competing patch.

## Correct grammar boundary

`systemd.exec` defines each whitespace-separated item as:

```text
source[:destination[:rbind|norbind]]
```

Destination and option are optional, but the option cannot be supplied while destination is omitted. Therefore `source::norbind` is invalid syntax, not a compatibility requirement. The initial workspace assumption that an empty destination field was meaningful was corrected before source execution.

The parser needs two tokenization levels:

1. coalesced shell-like whitespace between complete tuples;
2. non-coalesced colon fields inside each tuple.

## Installed baseline observation

Debian 13 systemd 257 emits empty-path warnings when repeated spaces, mixed whitespace, or line-continuation indentation appear between otherwise valid entries. Both writable and read-only directives reach the same parser boundary.

## Active source identities

```text
canonical base: 63e35ca3f99566095c84248e9eb41a3a6b32f2eb
active PR head: d32993d1f67ec1b42719c89eeda9425042df57ce
active canonical PR: systemd/systemd#43217
```

The PR changes:

```text
src/core/load-fragment.c
src/core/execute-serialize.c
src/test/test-load-fragment.c
src/test/test-execute.c
test/test-execute/exec-bindpaths.service
```

It rewrites configuration tuple extraction and execution-context serialization/deserialization. Parser evidence alone is therefore necessary but not sufficient.

## Durable parser fixture

```sh
SYSTEMD_ANALYZE=/path/to/systemd-analyze \
  bash investigations/systemd-bind-path-whitespace-overlap/reproduce.sh OUTPUT
```

The fixture runs cases independently and retains exact units, analyzer/kernel identity, status, stdout/stderr, hashes, and cleanup.

Valid cases include:

- source only;
- source and destination;
- complete `rbind` and `norbind` triples;
- ordinary one-space lists;
- repeated spaces, tabs, mixed whitespace, and continued indentation;
- quoted paths containing spaces;
- escaped literal colons;
- leading `-` ignore-missing marker;
- reset-to-empty followed by a new entry.

Invalid cases include omitted destination with option, too many fields, and unsupported options.

## Superseded harness failure

Initial run `30759715925` checked out both exact sources and installed dependencies but passed only `systemd/build` to Meson. Both jobs failed before configuration because the source directory was omitted.

```text
canonical artifact: 8838880432
canonical digest: sha256:65b940618c63baefaf6dde22a95febb2f47ce6cea5d6ddef82b0f90417864797
active PR artifact: 8839366457
active PR digest: sha256:fba8903937e894d5356c0f88eb4a7551f2372f2e49f19d557d46c0ba2a331155
```

The bounded repair used `meson setup systemd/build systemd` and added a workflow-contract regression. No product conclusion is taken from the failed run.

## Completed exact parser comparison

```text
Linux Fieldwork run: 30795425735
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

Both exact source states configured and built `systemd-analyze`. Every corrected grammar fixture executed.

Observed split:

- canonical base emits repeated empty-path warnings for continued indentation, repeated spaces, and mixed tabs/spaces;
- active PR accepts those forms with the same clean parser result as ordinary one-space syntax;
- quoted spaces and escaped colons remain accepted;
- source-only, source/destination, markers, options, and reset behavior remain on the expected paths;
- invalid options remain rejected;
- omitted destination with an option remains malformed rather than silently accepted;
- too many fields receive the more precise `Too many parameters in BindPaths=` diagnostic instead of being folded into an invalid option.

This supports the active parser rewrite over the tested documented grammar surface.

## Current serialization gate

The PR changes serialized bind-mount quoting and replaces duplicate deserialization logic with a shared tuple parser. A direct round-trip is now executing in the controlled systemd fork:

```text
repository: teamleaderleo/systemd
branch: fieldwork/43217-bind-serialize-roundtrip
head: d137ab24b2fc4b5371a804e38a1b5e67fc251ace
internal draft PR: teamleaderleo/systemd#8
focused run: 30849764916 — queued at last check
```

The branch commits two carrier files and no systemd product source. Its workflow checks out both canonical base and active PR head, then injects one source-native core test in the disposable checkout.

The test constructs six bind mounts covering:

- writable/read-only;
- `rbind`/`norbind`;
- ignore-missing;
- spaces;
- literal colons;
- quotes;
- backslashes;
- identical source and destination.

For each source state it:

1. serializes a complete invocation to memory;
2. deserializes into a fresh `ExecContext`;
3. compares every bind-mount field in order;
4. serializes the restored context again;
5. requires byte-identical serialized output;
6. runs the test under Valgrind;
7. retains exact wire text, source patch, logs, and binary identity.

The carrier was self-reviewed before execution. A proposed “stderr must be empty” assertion was removed because the systemd test framework may emit successful diagnostic logging; exit status, field equality, deterministic reserialization, and Valgrind remain the gates.

## Next decision

Classify run `30849764916` by first failing step. If both base and PR pass, compare the retained wire forms and confirm the new format is a compatible canonicalization rather than a field-loss change. If only the PR fails, inspect the first mismatched field. If only base fails, determine whether the new parser/serializer deliberately closes an old escaping hole. Do not infer serialization correctness from parser success alone.

## Publication boundary

No canonical systemd issue comment, pull request, review, reaction, email, or maintainer contact is authorized or made.
