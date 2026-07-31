# Chrootless environment harness safety repair

Date: 2026-07-31

Tracking: issue #130. Related product work: issues #40 and #69, PRs #74 and #109.

## TL;DR

The reusable chrootless environment probe can recursively remove below any caller-selected `RUNNER_TEMP` except `/`, and it changes the imported `mmdebstrap` executable mode in the checkout. This candidate accepts only named disposable parent families, validates the actual derived deletion target, and runs a preserved temporary source copy.

Review repaired two evidence holes:

1. preserve the exact incoming source mode, bytes, and Git status instead of demanding a globally clean checkout;
2. reject overlap between the derived `$runtime_parent/mmdebstrap-chrootless-env` target and the repository or home in either direction.

## Explain like I'm five

The test needs a sandbox it can throw away. Today the caller can point it near important files, and the test says “that is fine as long as the path is not `/`.”

The repair accepts only known trash areas, checks the exact box it will delete, and makes a photocopy of the program before marking it executable. At the end, the original must look exactly as it did at the beginning.

## Why care

A reusable probe should be safe when a person runs it outside GitHub Actions. A caller-selected parent such as `/etc`, a home directory, or the repository can place recursive cleanup in the wrong neighborhood. Changing imported source mode also dirties the checkout and makes later tests depend on hidden state.

Checking only the parent is insufficient. A checkout at `/tmp/mmdebstrap-chrootless-env/repository` makes `/tmp` look safe even though the fixed runtime target is an ancestor of the checkout and `rm -rf` would erase it.

A blanket clean-tree requirement creates another problem: it refuses a checkout that already contains deliberate local work. Exact before/after preservation is the stronger invariant.

## Confirmed baseline

Current `investigations/mmdebstrap-chrootless-env/run.sh`:

- canonicalizes `${RUNNER_TEMP:-/tmp}`;
- rejects only `/`;
- derives `$runtime_parent/mmdebstrap-chrootless-env` and later runs `rm -rf` on it;
- runs `chmod 0755 "$source_root/mmdebstrap"` directly in the imported tree.

The normal hosted path was disposable, so retained product evidence remains useful. The reusable local contract is unsafe and non-idempotent.

## Candidate

`0002-guard-runtime-and-source-copy.patch`:

- introduces `--check-runtime-parent PATH` for a small executable safety gate;
- accepts `/tmp`, `/var/tmp`, and the hosted `/home/runner/work/_temp` family;
- canonicalizes both the selected parent and fixed runtime target;
- rejects root, other parent families, parent-component collapse, and repository/home overlap;
- rejects both `runtime inside protected path` and `runtime contains protected path` relationships;
- keeps the runtime as a strict child of the accepted parent;
- copies imported `mmdebstrap` with mode preservation into `$runtime/source/mmdebstrap`;
- marks and executes only the runtime copy;
- snapshots original mode, Git blob hash, and path-specific Git status;
- requires all three values to match before reporting success.

## Why this approach

An allowlist fits this probe because its cleanup parent has only three legitimate families. General ownership or writability checks would accept many important directories and create check-then-use ambiguity. Prefix checks alone would still mishandle `..` and symlinks unless paths are canonicalized first.

The destructive object is the derived runtime, not the caller's parent. Checking both overlap directions protects a repository or home that is either an ancestor or descendant of that target.

Copying the source preserves the imported tree as evidence. Restoring the mode afterward would leave interruption paths able to strand the checkout in a changed state.

Mode, content hash, and Git status cover three distinct outcomes:

- executable permission changed;
- file bytes changed;
- the checkout's tracked/untracked state changed.

Comparing before and after supports both a clean checkout and deliberate pre-existing local modifications.

## Historical precedent

- Issue #75 requires the privileged workflow to validate code origin instead of trusting a branch name.
- PR #72 showed that generated tests need stable absolute command paths after directory changes.
- PR #109's corrected probes already use explicit disposable-parent families and preserved runtime copies.
- `FIELD_GUIDE.md` calls the unsafe path pattern “Guarded but unresolved” and requires resolution before recursive deletion.

## Focused regression

`tests/test_mmdebstrap_chrootless_env_harness_safety_patch.py`:

- applies the exact retained patch;
- runs shell syntax validation;
- accepts the three named disposable parent families and descendants;
- rejects root, repository, home, and `/tmp/../etc`;
- creates disposable Git repositories both inside the fixed runtime and containing it, and requires rejection;
- creates home paths both inside and equal to the fixed runtime, and requires rejection;
- requires preserved-source copying and runtime execution;
- forbids chmod of the imported source;
- requires mode, content, and Git-state snapshots and comparisons;
- proves the baseline contains both original defects.

## Evidence boundary

The focused test exercises the safety classifier and patch contract with real canonical paths and disposable Git repositories. It does not run the full package transaction, race a hostile process between validation and deletion, or prove behavior on non-GNU systems lacking the same `realpath` and `stat` options.

## Disposition

`REPAIR` until exact-head CI validates clean patch application and both workflows execute on the reviewed head. After a green focused run, the patch is suitable for direct application or extraction into a current-main candidate.

## Authority

Internal Linux Fieldwork harness repair only. No upstream contact is included or authorized.
