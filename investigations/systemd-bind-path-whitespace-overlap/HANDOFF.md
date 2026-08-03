# Handoff — systemd bind-path whitespace overlap

Handoff date: 2026-08-03  
State: `ACTIVE — REPAIRED BASE/PR SOURCE COMPARISON QUEUED`  
External contact authorized: `false`  
External contact made: `none`

## Exact source boundary

```text
canonical issue: systemd/systemd#43214
active canonical PR: systemd/systemd#43217
canonical base: 63e35ca3f99566095c84248e9eb41a3a6b32f2eb
active PR head: d32993d1f67ec1b42719c89eeda9425042df57ce
controlled product branch: none
Linux Fieldwork workflow: .github/workflows/systemd-bind-path-source-compare.yml
```

## Demonstrated mechanism

Repeated whitespace is interpreted through the same no-coalescing separator treatment used for colon fields. Whitespace separates complete bind tuples; colon separates fields inside a tuple. Repeated whitespace must coalesce without changing colon-field parsing.

Installed Debian 13 systemd 257 reproduced empty-path warnings for repeated spaces and line-continuation indentation.

## Corrected grammar finding

`systemd.exec` documents:

```text
source[:destination[:rbind|norbind]]
```

and requires the option string to be omitted when destination is omitted. Therefore `source::norbind` is invalid syntax, not compatibility behavior. The fixture tests this as a negative control.

## First source-comparison run

```text
run: 30759715925
canonical-base job: 91527946682
active-PR job: 91527946711
```

Both jobs checked out and verified the intended exact source. Both failed before compilation for the same carrier-owned reason:

```text
ERROR: Neither source directory 'systemd/build' nor build directory None contain a build file meson.build.
```

The workflow invoked:

```text
meson setup systemd/build ...
```

from the parent checkout directory. Meson therefore interpreted `systemd/build` as a source directory. The correct invocation names both directories:

```text
meson setup systemd/build systemd ...
```

No parser, serialization, or product result was executed in run `30759715925`.

Retained artifacts:

```text
canonical base
  artifact: 8838880432
  digest: sha256:65b940618c63baefaf6dde22a95febb2f47ce6cea5d6ddef82b0f90417864797
  load-fragment blob: bf17e2df46f018934346a991617f69b30ca7a892
  execute-serialize blob: 5503925226e238bc039346bf1055a744367c7a0c
  test-execute blob: 1c7c8c8d6f9becca5c927feac427bb88040fa847
active PR
  artifact: 8839366457
  digest: sha256:fba8903937e894d5356c0f88eb4a7551f2372f2e49f19d557d46c0ba2a331155
  load-fragment blob: cced46d969833bd05c914c99959caab3cb02b542
  execute-serialize blob: c7f84b4c16cc2773cfe69aa9f1a5cc14a5c810b8
  test-execute blob: aba862ed8d744afc47f76deb69a2a011ca73085b
```

## Repaired carrier

Linux Fieldwork commit `8a909171aac4944e27ae257af1fba6aaae21bdad` changes only the Meson source/build-directory ownership. The exact source matrix, fixture, artifact boundary, and comparison logic remain unchanged.

## Durable fixture

```text
investigations/systemd-bind-path-whitespace-overlap/reproduce.sh
```

It executes cases independently and retains per-case status, stdout, stderr, and hashes for:

- repeated, tab/mixed, and continuation whitespace;
- ordinary one-space syntax;
- source-only, source/destination, and full triples;
- quoted spaces and escaped colons;
- ignore-missing marker;
- reset assignment;
- omitted destination with options;
- too many fields;
- invalid option.

## First incomplete step

Resolve the first completed systemd comparison run at or after Linux Fieldwork commit `8a909171...` and classify in this order:

1. dependency/configure/build ownership;
2. analyzer identity and digest;
3. every valid and invalid parser case;
4. whether PR #43217 removes only repeated-whitespace empty-path warnings;
5. quoted-space and escaped-colon compatibility;
6. source-native tests covering execution-context serialization and deserialization.

Do not infer serialization safety from `systemd-analyze verify`. After parser comparison, run the narrowest exact source-native round-trip test that reaches the changed serialization code.

## Publication boundary

No canonical comment or review is authorized. Retain findings internally until the user explicitly approves public communication.

## Cleanup state

No local systemd checkout or build survives. Hosted jobs use disposable runners and bounded artifacts. No service, mount, namespace, credential, or canonical repository state is changed.
