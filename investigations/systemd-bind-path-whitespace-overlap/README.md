# systemd bind-path whitespace overlap review

State: `ACTIVE OVERLAP REVIEW — NO COMPETING SOURCE PATCH`  
Canonical issue: `systemd/systemd#43214`  
Active implementation: `systemd/systemd#43217`  
External contact authorized: `false`  
External contact made: `none`

## Question

Can systemd ignore repeated whitespace between `BindPaths=` and `BindReadOnlyPaths=` entries while preserving meaningful empty colon fields, quoting, escaped colons, and execution-state serialization?

## Baseline observation

On Debian 13 with systemd 257, repeated spaces between bind entries produced empty-path warnings. Line-continuation indentation produced multiple equivalent warnings. Both `BindPaths=` and `BindReadOnlyPaths=` reach the same parser boundary.

The parser separates fields using colon and whitespace while deliberately disabling separator coalescing. Disabling coalescing is necessary for forms such as:

```text
source::options
```

where the empty destination field is meaningful. Applying the same no-coalescing behavior to whitespace causes repeated inter-entry spaces to become empty path entries.

A reusable verifier fixture is retained as `reproduce.sh`.

## Active overlap

Upstream PR `systemd/systemd#43217`, head checked at:

```text
d32993d1f67ec1b42719c89eeda9425042df57ce
```

The PR is broader than a one-line leading-whitespace skip. It changes:

- bind-path parser extraction;
- internal representation behavior;
- execution-context serialization/deserialization;
- unit tests;
- execution tests covering quoted spaces and escaped colons.

Because an active implementation already owns the source change, this investigation must not create a competing public patch.

## Distinguishing review matrix

The active implementation should be tested for:

1. repeated spaces between ordinary entries;
2. tab and mixed-whitespace separators;
3. line-continuation indentation;
4. exact `source::options` empty destination field;
5. quoted source and destination paths containing spaces;
6. escaped literal colons;
7. leading `-` ignore-missing marker;
8. read-only and recursive markers;
9. execution-context serialization and deserialization round-trip;
10. reset-to-empty assignment behavior;
11. malformed trailing colon fields;
12. no change to already valid one-space syntax.

## Reproducer

```sh
bash investigations/systemd-bind-path-whitespace-overlap/reproduce.sh
```

The script creates three temporary service files:

- repeated-space failure case;
- continued-line indentation case;
- empty-colon-field compatibility control.

It runs `systemd-analyze verify`, retains identity, status, stdout/stderr hashes, and service fixtures, then removes its temporary directory.

## Current interpretation

The defect is real and shared, but the right patch boundary is not simply “coalesce all separators.” Whitespace and colon have different syntax roles. The active PR's broader parser rewrite may be justified, but it needs compatibility evidence proportional to that breadth.

## Next step

Run the fixture against:

1. current canonical baseline;
2. the exact active PR head;
3. a minimal whitespace-only alternative in a disposable comparison branch, only if needed for design discrimination.

Compare diagnostics, parsed entries, and serialization. Retain the result as review evidence. Do not post it upstream without explicit authorization.
