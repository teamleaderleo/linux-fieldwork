# uutils `rm -r`: deep traversal without one descriptor per level

## TL;DR

Current Unix `rm` uses fd-relative traversal to resist symlink swaps, but its recursive call chain retains one open directory descriptor for every ancestor. A sufficiently deep tree reaches `EMFILE` and cannot be removed.

Replacing this with path recursion or plain `remove_dir_all` would trade the resource defect for path-length and race defects. A plausible safe design keeps a stable root anchor, stores directory-entry names plus device/inode identities, and reopens the parent frame by replaying components from the root anchor. Any identity mismatch must abort that branch rather than delete a replacement.

This investigation remains in `SCOPING`. No source candidate should be written until the replay invariant, root removal, interactive prompts, mount boundaries, and deterministic low-RLIMIT test are fully specified.

## Explain like I'm five

The current remover walks down a staircase while keeping every door behind it open so it can walk back up. A very deep staircase runs out of doors it is allowed to keep open.

Closing every old door is not enough, because someone might move the staircase while the remover is below. To return safely, it needs a fixed starting door and a list of which exact rooms it passed through. When it reopens the route, every room must still have the same identity.

## Why care

The defect prevents removal of real package-test and archive-generated trees. The original report came from an APT integration fixture. Current reports show the modern implementation can still fail or leave confusing `Directory not empty` diagnostics after an earlier traversal failure.

A careless repair could be worse: recursive deletion is destructive, and path re-resolution can descend into or unlink an attacker-provided replacement.

## Current state

- State: `SCOPING`
- Canonical source head reviewed: `uutils/coreutils@a0cb02453f314bdd3addda6f321f7e03adceb56b`
- Issues: `#7995`, related `#7324`
- Matching active PR found: none at the recorded search boundary
- Source candidate: none
- First incomplete step: formalize a bounded-descriptor traversal state machine and deterministic rename negative controls
- External-contact state: no canonical-upstream contact authorized or made

## Intent and history

Issue `#7324` records an older long-path problem and proposed changing directories during recursion. Issue `#7995` originally implicated the standard library fallback and open handles. Since then, uutils replaced the relevant Unix removal path with its own `DirFd`-relative safe traversal.

The current source no longer has the same implementation owner described in the early comments, but the resource shape remains: `safe_remove_dir_recursive_impl()` receives a borrowed parent `DirFd`, opens a child `DirFd`, and recursively calls itself before the parent descriptor can be dropped.

Recent project work explicitly moved destructive recursive utilities toward `openat`, `fstatat`, `O_NOFOLLOW`, and `unlinkat`. Any repair must preserve that direction.

## Question

Can recursive removal use a descriptor budget independent of tree depth while preserving:

- no-follow descent;
- entry identity;
- mount/device boundary checks;
- interactive prompting;
- long-path support;
- correct error aggregation;
- safe post-order unlinking?

## Source

- Project: uutils/coreutils
- Canonical revision: `a0cb02453f314bdd3addda6f321f7e03adceb56b`
- Relevant files:
  - `src/uu/rm/src/platform/unix.rs`
  - `src/uucore/src/lib/features/safe_traversal.rs`
  - `tests/by-util/test_rm.rs`
- Imported source: none; exact Git identity is the source boundary

## Baseline architecture

The Unix remover:

1. opens the command-line directory as a `DirFd`;
2. reads entry names relative to that descriptor;
3. uses `stat_at(..., NoFollow)`;
4. opens child directories with `open_subdir(..., NoFollow)`;
5. recurses while retaining the parent descriptor;
6. unlinks the child through the retained parent descriptor after its contents are removed.

This is strong against simple symlink swaps and multi-component path re-resolution, but open descriptor count grows linearly with depth.

## Why the obvious fixes fail

### Break recursion into path-based calls

Reopening `path.join(child)` reintroduces multi-component path resolution and PATH_MAX exposure. A replacement above the child can redirect traversal.

### Use `std::fs::remove_dir_all`

This abandons the project's fd-relative security work and has its own historical deep-path/descriptor limitations.

### Open `..` from the child after recursion

This bounds descriptor use, but an open directory can be renamed into another parent. Its `..` can then identify the new parent, not the original frame that still owns sibling state. Unlinking the original child name could target a replacement.

### Keep periodic ancestor descriptors

This reduces the growth rate but does not make the descriptor bound independent of depth. It also leaves checkpoint/replay semantics unresolved.

## Candidate state-machine direction

A safer design can separate **diagnostic state** from **open-handle state**.

### Stable anchors

Keep:

- a descriptor for the command-line root directory;
- a descriptor for the root's parent when needed for final unlink;
- one current traversal descriptor;
- at most one temporary descriptor during component replay.

This requires a safe `DirFd` duplication operation or equivalent ownership arrangement so the root anchor remains available while the current descriptor descends.

### Stored frame data

Each frame can retain memory-only state:

- component name relative to its parent;
- diagnostic `PathBuf` that is never used for destructive syscalls;
- device and inode from the opened directory descriptor;
- mode and device information needed for prompts and mount policies;
- remaining entry names/index;
- accumulated child error state.

### Descent

- Open the child relative to the current descriptor with `NoFollow`.
- Capture `fstat` identity from the opened child.
- Push the parent frame without retaining its descriptor.
- Make the child descriptor current.

### Ascent/replay

To resume a stored parent frame:

1. duplicate the stable root descriptor;
2. replay stored component names one at a time with `open_subdir(..., NoFollow)`;
3. after each open, compare device/inode with the identity stored in the corresponding frame;
4. drop the previous temporary descriptor before opening the next component;
5. abort safely on missing, replaced, moved, or mismatched components;
6. use the verified reopened parent descriptor to unlink the completed child entry.

The replay can cost more syscalls, potentially quadratic in a single deep chain, but has a constant descriptor budget and avoids constructing a syscall path longer than one component.

## Root and rename boundaries

The command-line root needs separate treatment:

- retaining the root descriptor pins the traversed object even if its pathname changes;
- final removal through the original parent/name must verify that the parent entry still refers to the pinned root identity;
- if the root was renamed or replaced, refuse to unlink a different object;
- the open root may still be emptied, so the error/cleanup policy for a moved root must be explicit.

These semantics need comparison against GNU executable behavior and the project's existing race-hardening expectations before implementation.

## Mount and policy boundaries

Stored frame metadata must preserve the current distinctions:

- `--one-file-system` compares descendants to the traversal root device;
- `--preserve-root=all` compares a directory to its immediate parent device;
- interactive prompts depend on mode, readability, writability, emptiness, and command-line status;
- a skipped or failed child must prevent incorrect parent removal without duplicating secondary errors.

Replay must not recompute these policies from a possibly replaced path.

## Deterministic test plan

A useful test should lower `RLIMIT_NOFILE` and create a deep tree without requiring a pathname over system limits.

Candidate checks:

1. Build a nested tree one component at a time using relative `mkdirat`/directory changes.
2. Set a descriptor limit low enough that the current one-fd-per-level implementation fails.
3. Run candidate `rm -r` and assert successful complete removal.
4. Add a rename/replacement negative control that changes an ancestor between descent and replay; assert the candidate refuses the replacement rather than deleting it.
5. Retain or extend syscall-level safe-traversal checks so no destructive multi-component `AT_FDCWD` path appears.

The race control likely needs a test-only synchronization hook or deterministic helper-level state machine rather than sleep-based timing.

## Stop signal

Do not write the source candidate until all of these are answered:

- how the root descriptor is duplicated and retained;
- how frame identity is represented portably;
- how replay handles a moved ancestor;
- how the final root unlink verifies identity;
- how interactive and mount policies are carried without path restat;
- how the test deterministically schedules replacement;
- whether the syscall increase is acceptable or needs bounded checkpoints.

## Results

No product result yet. This record refines the problem from “replace recursion with a loop” to “design bounded-descriptor, identity-verified replay without path-based destructive operations.”

## Evidence boundary

The descriptor-growth conclusion follows current source structure; a current binary reproduction has not yet been run in this environment because the local runner cannot resolve GitHub to build the exact source. The original and recent issue reports establish real failures, but the exact failure depth varies by descriptor limit and process state.

## Next step

Prototype the traversal state machine as a pure frame/replay model or test-only helper before modifying destructive code. Review the model against current `rm` prompt, mount, and error semantics. Only then create a controlled source branch.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other contact has been authorized or made.