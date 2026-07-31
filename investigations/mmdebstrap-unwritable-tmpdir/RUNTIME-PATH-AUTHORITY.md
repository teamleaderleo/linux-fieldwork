# Runtime path authority for the unwritable-TMPDIR harnesses

State: `candidate-created — exact-head CI pending`

## TL;DR

The two repository-owned TMPDIR evidence harnesses used a fixed runtime leaf below caller-controlled `RUNNER_TEMP` and recursively removed that derived path without checking whether it contained the checkout or HOME.

The candidate centralizes path validation in `runtime_guard.sh`, validates the exact canonical deletion target before any recursive cleanup, exposes side-effect-free check mode, and preserves the merged signal lifecycle.

## Explain like I'm five

The test is allowed to throw away its own temporary box. Before throwing it away, it now checks both the cupboard and the exact box to make sure the project and the user's home are not inside it.

The check button only inspects the address. It never throws anything away.

## Why care

A safe-looking parent does not make the derived deletion target safe. If the checkout is nested below the fixed runtime leaf, startup cleanup can remove the checkout itself. Recursive cleanup authority must be established for the exact canonical path that will be deleted.

## Owning work

- issue: #284;
- merged signal-lifecycle source: PR #273 / merge `885225866cc4dc7a4998d3b96e0e883900666d8f`;
- candidate branch: `fix/unwritable-tmpdir-runtime-path-authority`;
- harnesses:
  - `run.sh`;
  - `deep_review.sh`;
- shared guard: `runtime_guard.sh`;
- focused regression: `tests/test_unwritable_tmpdir_runtime_guard.py`.

## Exact baseline

The merged scripts derived:

```sh
runtime_root="${RUNNER_TEMP:-/tmp}/FIXED-LEAF"
```

and later executed:

```sh
rm -rf "$runtime_root"
```

No canonical parent/runtime allowlist or repository/HOME overlap check preceded the first recursive removal.

## Disposable negative geometry

For either fixed leaf:

```text
selected parent: /tmp/disposable-parent
runtime:         /tmp/disposable-parent/FIXED-LEAF
repository:      /tmp/disposable-parent/FIXED-LEAF/repository
```

The parent belongs to a normal temporary family, but the exact runtime contains the checkout. Parent-only validation would still authorize the wrong deletion target.

The regression runs check mode from disposable Git repositories in both directions:

- runtime contains repository;
- runtime is inside repository.

Both checks must return 2 and preserve repository sentinels byte-for-byte.

## Candidate guard

`validate_disposable_runtime REPOSITORY HOME PARENT LEAF`:

1. rejects empty, dot, parent, and slash-containing leaves;
2. canonicalizes repository, HOME, selected parent, and exact runtime with `realpath -m`;
3. accepts only `/tmp`, `/var/tmp`, and `/home/runner/work/_temp` families, including descendants;
4. requires the canonical runtime to remain below the canonical selected parent;
5. rejects runtime equal to or inside the repository;
6. rejects runtime containing the repository;
7. rejects generic runtime/HOME overlap in both directions;
8. preserves the normal hosted `/home/runner` → `/home/runner/work/_temp` relationship while rejecting HOME equal to or below the runtime;
9. prints the canonical runtime only after every check passes.

The guard contains no cleanup command.

## Harness integration

Each harness declares its fixed leaf, sources the shared guard, and supports:

```text
SCRIPT --check-runtime-parent PATH
```

Check mode validates and exits before traps, directory creation, mode changes, result removal, or recursive cleanup.

Normal execution obtains `runtime_root` only from the validated guard output. Existing startup and exit cleanup then operate on that validated path. The merged once-only signal cleanup and result precedence are unchanged.

## Executable controls

The focused test covers:

- every allowed parent family and descendants;
- root, unlisted parents, and unsafe leaf values;
- runtime equal to, inside, and containing repository paths;
- existing parent symlink canonicalization before overlap checks;
- runtime inside HOME and runtime containing HOME;
- ordinary hosted HOME acceptance;
- hosted HOME equal to or below runtime rejection;
- both complete harnesses rejecting a runtime that contains their disposable checkout;
- both complete harnesses rejecting a runtime inside their disposable checkout;
- sentinel preservation for every rejected harness scenario;
- allowed check mode side-effect freedom and immediate repeatability;
- validation source ordering before the first `rm -rf "$runtime_root"`;
- removal of raw `RUNNER_TEMP/FIXED-LEAF` construction;
- complete Bash syntax for both harnesses and the shared guard;
- absence of recursive cleanup and mode changes from the guard itself.

The existing signal-lifecycle regression remains authoritative for INT/TERM status, once-only cleanup, primary-result precedence, and immediate rerun.

## Cleanup and safety

Dynamic tests use disposable paths below `/tmp`, disposable Git metadata, copied harness scripts, source-only guard invocation, and sentinel files. Check mode performs no deletion.

No full mmdebstrap run, package installation, network request, mount, namespace, root operation, public target, credential, or external-project action is required by the focused guard test.

## Evidence boundary

Canonical preflight validation does not pin directory identity. A hostile same-UID actor may rename or replace an ancestor after validation and before cleanup. Closing that race would require directory-descriptor-relative lifecycle ownership and is outside this candidate.

The candidate also does not change result-directory cleanup inside the repository, imported-source mode handling, or the semantic TMPDIR behavior under study.

## Disposition

`REPAIR CANDIDATE — HOLD FOR EXACT-HEAD CI AND COMPLETE FIVE-FILE REVIEW`.

Land only if repository discovery, both existing TMPDIR workflows, focused guard controls, Bash syntax, and the complete current diff pass on an unchanged mergeable head.

Internal Linux Fieldwork work only. External contact authorized: `false`.
