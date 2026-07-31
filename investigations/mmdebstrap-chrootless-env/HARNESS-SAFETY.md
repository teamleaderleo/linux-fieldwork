# Chrootless environment harness safety repair

Date: 2026-07-31

Tracking: issue #130. Related product work: issues #40 and #69, PRs #74 and #109.

## TL;DR

The reusable chrootless environment probe can recursively remove below any caller-selected `RUNNER_TEMP` except `/`, and it changes the imported `mmdebstrap` executable mode in the checkout. This candidate accepts only named disposable parent families and runs a preserved temporary source copy.

A second-pass review refined the final check: preserve the exact incoming source mode, bytes, and Git status. Requiring a globally clean source file would reject legitimate pre-existing local work.

## Explain like I'm five

The test needs a sandbox it can throw away. Today the caller can point it near important files, and the test says “that is fine as long as the path is not `/`.”

The repair accepts only known trash areas and makes a photocopy of the program before marking it executable. At the end, the original must look exactly as it did at the beginning.

## Why care

A reusable probe should be safe when a person runs it outside GitHub Actions. A caller-selected parent such as `/etc`, a home directory, or the repository can place recursive cleanup in the wrong neighborhood. Changing imported source mode also dirties the checkout and makes later tests depend on hidden state.

A blanket clean-tree requirement creates another problem: it refuses a checkout that already contains deliberate local work. Preservation is the stronger invariant.

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
- rejects root, other parents, repository paths, home paths, and parent-component collapse;
- keeps the runtime as a strict child of the accepted parent;
- copies imported `mmdebstrap` with mode preservation into `$runtime/source/mmdebstrap`;
- marks and executes only the runtime copy;
- snapshots original mode, Git blob hash, and path-specific Git status;
- requires all three values to match before reporting success.

## Why this approach

An allowlist fits this probe because its cleanup parent has only three legitimate families. General ownership or writability checks would accept many important directories and create check-then-use ambiguity. Prefix checks alone would still mishandle `..` and symlinks unless the parent is canonicalized first.

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
- requires preserved-source copying and runtime execution;
- forbids chmod of the imported source;
- requires mode, content, and Git-state snapshots and comparisons;
- proves the baseline contains both defects.

## Evidence boundary

The focused test exercises the safety classifier and patch contract. It does not run the full package transaction, race a hostile process between validation and deletion, or prove behavior on non-GNU systems lacking the same `realpath` and `stat` options.

## Disposition

`REPAIR` until exact-head CI validates clean patch application. After a green focused run, the patch is suitable for direct application or extraction into a current-main candidate.

## Authority

Internal Linux Fieldwork harness repair only. No upstream contact is included or authorized.
