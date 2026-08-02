# systemd bind-path whitespace overlap review

State: `ACTIVE OVERLAP REVIEW — CORRECTED GRAMMAR MATRIX`  
Canonical issue: `systemd/systemd#43214`  
Active implementation: `systemd/systemd#43217`  
External contact authorized: `false`  
External contact made: `none`

## Question

Can systemd ignore repeated whitespace between `BindPaths=` and `BindReadOnlyPaths=` entries while preserving every documented tuple form, quoting, escaped colons, markers, reset behavior, malformed-input diagnostics, and execution-state serialization?

## Baseline observation

On Debian 13 with systemd 257, repeated spaces between bind entries produced empty-path warnings. Line-continuation indentation produced multiple equivalent warnings. Both `BindPaths=` and `BindReadOnlyPaths=` reach the same parser boundary.

The parser historically used colon and whitespace as separators under a no-coalescing extraction mode. Colon separators describe fields inside one mount tuple, while whitespace separates complete tuples. Applying the same no-coalescing behavior to whitespace causes repeated inter-entry spaces to become empty path entries.

## Corrected documented grammar

`systemd.exec` defines each whitespace-separated item as a colon-separated triple:

```text
source[:destination[:rbind|norbind]]
```

The destination and option string are optional, but the documentation explicitly states:

```text
If the destination path is omitted, the option string must be omitted too.
```

Therefore `source::norbind` is an invalid control, not compatibility syntax. The earlier workspace text incorrectly treated an empty destination field as meaningful. That assumption has been removed from the fixture and handoff.

The corrected matrix now distinguishes:

### Valid controls

- source only;
- source and destination;
- complete triples using `rbind` and `norbind`;
- ordinary one-space lists;
- repeated, tab, mixed, and continued whitespace between tuples;
- quoted paths containing spaces;
- escaped literal colons;
- leading `-` ignore-missing marker;
- reset-to-empty assignment followed by a new entry.

### Invalid controls

- omitted destination with an option (`source::norbind`);
- too many colon fields;
- unsupported option strings.

## Active overlap

Upstream PR `systemd/systemd#43217` remains open at:

```text
base: 63e35ca3f99566095c84248e9eb41a3a6b32f2eb
head: d32993d1f67ec1b42719c89eeda9425042df57ce
```

The PR is broader than a leading-whitespace skip. It changes:

- configuration tuple extraction;
- bind-path representation handling;
- execution-context serialization and deserialization;
- quoting and escaping of serialized fields;
- parser and execution tests.

Because the active implementation already owns the source change, this investigation must not create a competing public patch.

## Durable fixture

```sh
bash investigations/systemd-bind-path-whitespace-overlap/reproduce.sh OUTPUT
```

Set `SYSTEMD_ANALYZE` to test a non-installed build:

```sh
SYSTEMD_ANALYZE=/path/to/build/systemd-analyze \
  bash investigations/systemd-bind-path-whitespace-overlap/reproduce.sh OUTPUT
```

The script runs every case independently and retains:

- exact service files;
- analyzer and kernel identity;
- status per case;
- stdout/stderr per case;
- SHA-256 values for every output;
- cleanup through a signal-safe temporary-directory trap.

## Source comparison plan

A controlled workflow should build and compare:

1. canonical base `63e35ca3...`;
2. exact PR head `d32993d...`.

The first stage is parser evidence through the built `systemd-analyze verify`. Serialization/deserialization needs a source-native test or a narrowly extracted existing test target; parser success alone is not sufficient to approve the broad PR.

## Current interpretation

The defect is real and shared. The parser needs two levels of tokenization:

1. coalesced shell-like whitespace between complete tuples;
2. non-coalesced colon fields inside each tuple.

The active PR follows that general shape. The remaining review question is whether its quoting, malformed-field, and serialized-state behavior exactly preserve documented semantics.

## Next step

Execute the corrected fixture against base and PR builds, retain artifacts, then inspect or run the source-native serialization tests. Do not post findings upstream without explicit authorization.
