# Runtime path authority for the unwritable-TMPDIR harnesses

State: `candidate repaired after complete review — final exact-head gates pending`

## TL;DR

The two repository-owned TMPDIR evidence harnesses used a fixed runtime leaf below caller-controlled `RUNNER_TEMP` and recursively removed that derived path without checking whether it contained the checkout or HOME.

The first guard repair centralized exact-path validation, but complete review found a second destructive distinction: resolving a pre-existing final runtime symlink and returning its target to `rm -rf` changed lexical symlink removal into recursive target deletion.

The current candidate rejects a pre-existing final-component symlink before canonicalizing and returning cleanup authority. It preserves repository, HOME, root, parent-family, signal-lifecycle, and rerun controls.

## Explain like I'm five

The test may throw away its own temporary box. It now checks that the project and HOME are not inside the box, and it refuses a box label that is secretly an arrow to a different box.

The check button only inspects the address. It never throws anything away.

## Why care

A safe-looking parent does not make the derived deletion target safe. Two different mistakes matter:

1. the fixed runtime leaf can contain the checkout or HOME;
2. the fixed runtime leaf can be a symlink, so canonicalization can redirect recursive cleanup to the symlink target.

Recursive cleanup authority must match the exact lexical object passed by the harness and must not silently broaden through final-component symlink resolution.

## Owning work

- issue: #284;
- carrier: PR #288;
- candidate branch: `fix/unwritable-tmpdir-runtime-path-authority`;
- merged signal-lifecycle source: PR #273 / merge `885225866cc4dc7a4998d3b96e0e883900666d8f`;
- stacked root repair: PR #292;
- harnesses: `run.sh` and `deep_review.sh`;
- shared guard: `runtime_guard.sh`;
- focused regressions:
  - `tests/test_unwritable_tmpdir_runtime_guard.py`;
  - `tests/test_unwritable_tmpdir_runtime_guard_root.py`.

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

## Checkout-overlap geometry

For either fixed leaf:

```text
selected parent: /tmp/disposable-parent
runtime:         /tmp/disposable-parent/FIXED-LEAF
repository:      /tmp/disposable-parent/FIXED-LEAF/repository
```

The parent belongs to a normal temporary family, but the exact runtime contains the checkout. Parent-only validation still authorizes the wrong deletion target.

The regression runs check mode from disposable Git repositories in both directions:

- runtime contains repository;
- runtime is inside repository.

Both checks return 2 and preserve repository sentinels byte-for-byte.

## Final-component symlink review finding

Reviewed head `e9fa4f89be02e816bfca7f5e548a16fe595e553b` computed:

```sh
runtime_root="$(realpath -m "$runtime_parent/$leaf")"
printf '%s\n' "$runtime_root"
```

Both harnesses then executed `rm -rf "$runtime_root"`.

Distinguishing geometry:

```text
/tmp/parent/FIXED-LEAF -> /tmp/parent/victim
/tmp/parent/victim/sentinel
```

The imported lexical cleanup `rm -rf /tmp/parent/FIXED-LEAF` removes the symlink itself. The reviewed candidate returned `/tmp/parent/victim`, so cleanup recursively targeted the directory and sentinel. Parent, repository, HOME, and allowed-family checks all passed because the target remained below the allowed parent.

This was a candidate-owned destructive semantic regression. It was checkpointed before repair in PR #288 review comment `5143593330`.

## Current guard contract

`validate_disposable_runtime REPOSITORY HOME PARENT LEAF`:

1. rejects empty, dot, parent, and slash-containing leaves;
2. canonicalizes repository, HOME, and selected parent with `realpath -m`;
3. rejects canonical repository `/` and HOME `/`;
4. accepts only `/tmp`, `/var/tmp`, and `/home/runner/work/_temp` parent families, including descendants;
5. constructs the lexical final runtime path below the canonical parent;
6. rejects that lexical final path when it is a symlink;
7. canonicalizes the non-symlink runtime path;
8. requires the canonical runtime to remain below the canonical selected parent;
9. rejects runtime equal to, inside, or containing the repository;
10. rejects generic runtime/HOME overlap in both directions;
11. preserves the normal hosted `/home/runner` to `/home/runner/work/_temp` relationship while rejecting HOME equal to or below runtime;
12. prints the canonical runtime only after every check passes.

The guard contains no cleanup or mode-changing command.

## Harness integration

Each harness declares its fixed leaf, sources the shared guard, and supports:

```text
SCRIPT --check-runtime-parent PATH
```

Check mode validates and exits before traps, directory creation, mode changes, result removal, or recursive cleanup.

Normal execution obtains `runtime_root` only from the successful guard. Existing startup and exit cleanup operate on that path. The merged once-only signal cleanup and result precedence are unchanged.

## Executable controls

The focused tests cover:

- every allowed parent family and descendants;
- root, unlisted parents, and unsafe leaf values;
- repository root and HOME root, including hosted-parent controls;
- runtime equal to, inside, and containing repository paths;
- existing parent symlink canonicalization before overlap checks;
- existing final runtime symlink rejection before canonicalization;
- direct final-symlink target and sentinel preservation;
- both complete harnesses rejecting final runtime symlinks and preserving targets/sentinels;
- runtime inside HOME and runtime containing HOME;
- ordinary hosted HOME acceptance and hosted HOME overlap rejection;
- sentinel preservation for every rejected harness scenario;
- allowed check-mode side-effect freedom and immediate repeatability;
- validation source ordering before the first recursive cleanup;
- removal of raw `RUNNER_TEMP/FIXED-LEAF` construction;
- complete Bash syntax for both harnesses and the shared guard;
- absence of recursive cleanup and mode changes from the guard;
- unique unittest discovery.

The existing signal-lifecycle regression remains authoritative for INT/TERM status, once-only cleanup, primary-result precedence, and immediate rerun.

## Executed evidence before this documentation refresh

Symlink-repair head `0d09f3d03b4bbddb1ee848942d0a5d04a49607d2` passed all three merge-ref gates against main `96a71a4cda1a4b8127520e79b7d6c021d0853b57`:

- Linux Fieldwork CI `30636187927` / 967;
- Verify explicit TMPDIR `30636187876` / 134;
- Deep TMPDIR review `30636187896` / 101.

Repository CI checked merge ref `c24ac0fe2d94ebe5cb834ccac3ade9201b89ad7e`, retained 349 of 372 discovered tests after removing 23 exact inherited duplicates, and passed all 349. Both direct and complete-harness final-symlink sentinel controls executed and passed.

Those runs establish the executable mechanism. This tracked-record refresh requires one final exact-head rerun before promotion.

## Cleanup and safety

Dynamic guard tests use disposable paths below `/tmp`, disposable Git metadata, copied harness scripts, source-only guard invocation, and sentinel files. Check mode performs no deletion.

The existing dedicated workflows run the repository-owned TMPDIR evidence harnesses under their documented disposable boundaries. No public target, credential, or external-project action is involved.

## Evidence boundary

Preflight validation does not pin directory identity. A hostile same-UID actor may rename or replace an ancestor or the final path after validation and before cleanup. Closing that race would require descriptor-relative lifecycle ownership and remains outside this candidate.

The candidate does not change result-directory cleanup inside the repository, imported-source mode handling, or the semantic TMPDIR behavior under study.

## Disposition

`REPAIR COMPLETE — HOLD FOR FINAL EXACT-HEAD REPOSITORY, EXPLICIT-TMPDIR, AND DEEP-REVIEW GATES`.

Land only if all three intended jobs execute on the unchanged final head, the current merge ref remains suitable, and a final six-file review finds no new blocker.

Internal Linux Fieldwork work only. External contact authorized: `false`.
