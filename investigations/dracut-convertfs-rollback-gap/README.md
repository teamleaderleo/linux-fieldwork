# dracut convertfs rollback gap

## TL;DR

At dracut commit `5d2bda46f4e75e85445ee4d3bd3f68bf966287b9`, `modules.d/30convertfs/convertfs.sh` can leave a converted root with `/bin` missing if the `ln -sfn usr/bin "$ROOT/bin"` step fails or is interrupted after the script has already moved the original `/bin` to `/bin.usrmove-old`.

The rollback function sees the backup, but first tries to move the current `/bin` to `/bin.del~`. At this exact transition point current `/bin` does not exist yet. That `mv` fails under the script's active `set -e`, aborting `cleanup()` before `/bin.usrmove-old` is restored. Exact-source execution reproduced this with an injected `ln` failure and with `SIGINT`.

`SIGTERM` and `SIGHUP` expose a second lifecycle gap: the script has an explicit `SIGINT` trap but no TERM/HUP traps. At the same handoff point, exact-source runs terminated by TERM/HUP skipped rollback entirely and left `/bin` missing with both `.usrmove-old` backups present.

A local two-part candidate — tolerate an absent current path in `cleanup()`, and route HUP/TERM through exit statuses that trigger the existing EXIT rollback — restored the original tree in the injected `ln` failure, SIGINT, SIGTERM, and SIGHUP cases. No upstream contact has been made.

## Explain like I'm five

`convertfs` is moving an old Linux layout into `/usr`. During one step it does this:

```text
/bin exists
→ move /bin to /bin.usrmove-old
→ create /bin as a symlink to usr/bin
```

There is a short moment between those two commands where `/bin` is supposed to be absent.

If symlink creation fails in that moment, rollback should put the old directory back. Instead rollback first tries to move the already-missing `/bin` out of the way. That command fails, rollback stops, and the saved original stays parked at `/bin.usrmove-old`.

Literal reduced outcome from exact current source:

```text
original /bin → moved to /bin.usrmove-old → ln fails → cleanup starts
→ cleanup tries to move missing /bin → cleanup aborts → /bin remains missing
```

## Why care

`convertfs` changes core filesystem paths during a usr-merge conversion. `/bin` is a basic command path. Leaving it absent while the original remains parked under `.usrmove-old` is a partial conversion state that can break later boot or recovery commands.

The scope is narrow: this investigation exercises the explicit `rd.convertfs` conversion path, not ordinary dracut image generation or modern systems that are already usr-merged.

## Current state

- State: `REVIEW`
- Exact working head: `dracutdevs/dracut@5d2bda46f4e75e85445ee4d3bd3f68bf966287b9`
- Exact source blob: `modules.d/30convertfs/convertfs.sh` = `58fa56df7d43fe77a97fb4a05cbeb898b008d07f`
- Latest authoritative gate: exact-source disposable-root matrix on Bash 5.2.37 — normal, early `cp` failure, injected `ln` failure, SIGINT, SIGTERM, SIGHUP, plus local candidate reruns
- First incomplete step: no full initramfs/QEMU execution and no owned-fork source branch
- Cleanup state: disposable `/tmp` roots, wrappers, and copied source removed after the run; no mounts, services, or external state created
- Next safe action: reproduce once in a dracut test context or owned fork, then decide whether to prepare a small source candidate and focused regression test
- External-contact state: no upstream contact authorized or made

## Intent and precedent

The rollback intent is explicit in current source immediately above `cleanup()`:

> `# clean up after ourselves no matter how we die.`

The same comment, EXIT trap, and SIGINT-only trap were already present in the original usr-move module added by commit `ae8b82e395c9530a66288f7a9e939242137d3f56` in 2012. The current code therefore preserves a long-standing rollback design rather than a recent refactor.

Relevant source:

- https://github.com/dracutdevs/dracut/blob/5d2bda46f4e75e85445ee4d3bd3f68bf966287b9/modules.d/30convertfs/convertfs.sh
- https://github.com/dracutdevs/dracut/blob/5d2bda46f4e75e85445ee4d3bd3f68bf966287b9/modules.d/30convertfs/do-convertfs.sh
- https://github.com/dracutdevs/dracut/commit/ae8b82e395c9530a66288f7a9e939242137d3f56

A separate historical decision moved `/var/run` and `/var/lock` conversion to the start intentionally so those links are fixed even when the rest of the system is already converted (`9d5e3ed74025a179f632daad933322f376b96f05`). That history explains the early var conversion and does not explain the `/bin` rollback gap described here.

Searches for `convertfs SIGTERM` and `rd.convertfs signal cleanup` found no matching GitHub issues in the repository during this pass.

## Question

Does current `convertfs.sh` restore the original root-tree state when failure or interruption occurs during the handoff from a real `/bin` directory to the new `/bin -> usr/bin` symlink?

## Source

- Project: `dracutdevs/dracut`
- Requested revision: repository default branch `master`
- Resolved commit: `5d2bda46f4e75e85445ee4d3bd3f68bf966287b9`
- Candidate source commit: none; local uncommitted candidate only
- Relevant source path: `modules.d/30convertfs/convertfs.sh`
- Relevant source blob: `58fa56df7d43fe77a97fb4a05cbeb898b008d07f`
- Hook path: `modules.d/30convertfs/do-convertfs.sh`
- Hook blob: `6ce31cb3ce5d16eb0620a20fb7efcabb5e8515af`
- Import metadata: source was read through the GitHub connector; no Fieldwork `upstream/` import was created in this pass

The locally executed copy was verified before testing:

```sh
git hash-object /tmp/convertfs-upstream.sh
# 58fa56df7d43fe77a97fb4a05cbeb898b008d07f
```

That equals the Git blob SHA returned for the exact upstream file.

## Environment

- Distribution/release: isolated execution container supplied by the ChatGPT tool runtime; distro identity was not relied on for the claim
- Kernel: `Linux 6.18.35`, x86_64
- Shell: `GNU bash 5.2.37(1)-release`
- Privileges: uid 0 inside the disposable container
- Context: disposable `/tmp` directory trees only; no chroot, mount, VM, service, or host root modification
- Relevant tools: GNU coreutils `cp`, `mv`, `ln`, `rm`; Python 3 only for deterministic signal delivery in the signal matrix

## Baseline behavior

A minimal disposable root contained:

```text
ROOT/bin/root-tool
ROOT/usr/bin/usr-tool
ROOT/var/
```

`ismounted` was wrapped to return false so the script took its existing hard-link copy path. A PATH wrapper around `ln` observed the root `/bin` symlink step while delegating normal behavior to `/bin/ln`.

With no injected failure, the exact current source completed with exit `0`:

```text
bin: symlink -> usr/bin
bin.usrmove-old: absent
usr/bin.usrmove-old: absent
usr/bin/root-tool: present
usr/bin/usr-tool: present
```

`ldconfig -r` complained because the reduced root lacked a normal `/etc`; the script intentionally runs that phase after `set +e`, printed `Done.`, and exited `0`. That late reduced-root warning is outside this finding.

An early injected first-`cp` failure was the negative control for rollback:

```text
exit: 42
/bin: original directory present
/bin.usrmove-old: absent
/usr/bin.usrmove-old: absent
/usr/bin.usrmove-new: absent
```

The output included `Something failed. Move back to the original state`. This shows rollback is capable of working before the two-step `/bin` handoff.

## Hypothesis or candidate

### Baseline hypothesis

Rollback assumes the current destination exists whenever a `.usrmove-old` backup exists:

```sh
if [[ -d "${dir}.usrmove-old" ]]; then
    mv "$dir" "${dir}.del~"
    mv "${dir}.usrmove-old" "$dir"
    rm -fr -- "${dir}.del~"
fi
```

The root-directory switch itself violates that assumption transiently:

```sh
mv "$ROOT/$dir" "$ROOT/${dir}.usrmove-old"
ln -sfn usr/$dir "$ROOT/$dir"
```

After the `mv` and before a successful `ln`, the backup exists while the current path is absent.

### Local candidate tested

The local candidate guarded the move of the current path:

```sh
if [[ -d "${dir}.usrmove-old" ]]; then
    if [[ -e "$dir" || -L "$dir" ]]; then
        mv "$dir" "${dir}.del~"
    fi
    mv "${dir}.usrmove-old" "$dir"
    rm -fr -- "${dir}.del~"
fi
```

It also added signal entries so TERM/HUP produce nonzero exit states before the existing EXIT trap runs:

```sh
trap 'exit 129;' SIGHUP
trap 'exit 1;' SIGINT
trap 'exit 143;' SIGTERM
```

Those signal values preserve the conventional shell-visible `128 + signal` statuses for HUP and TERM while retaining current SIGINT status `1`. A future source candidate should decide deliberately whether callers need true `waitpid()` signal identity or only shell exit status; this pass tested rollback behavior, not that interface choice.

## Reproduction

Start from the exact revision and verify the source blob:

```sh
git checkout 5d2bda46f4e75e85445ee4d3bd3f68bf966287b9
test "$(git hash-object modules.d/30convertfs/convertfs.sh)" = \
  58fa56df7d43fe77a97fb4a05cbeb898b008d07f
```

Create a disposable root:

```sh
ROOT=$(mktemp -d)
mkdir -p "$ROOT/bin" "$ROOT/usr/bin" "$ROOT/var"
printf 'root\n' > "$ROOT/bin/root-tool"
printf 'usr\n' > "$ROOT/usr/bin/usr-tool"
```

Put wrappers first in `PATH`. `ismounted` keeps the test on one filesystem. The `ln` wrapper injects a failure only for the root `/bin` handoff:

```sh
WRAP=$(mktemp -d)
cat > "$WRAP/ismounted" <<'EOF'
#!/bin/sh
exit 1
EOF

cat > "$WRAP/ln" <<'EOF'
#!/bin/bash
if [[ ${!#} == "$TARGET_ROOT/bin" ]]; then
    exit 42
fi
exec /bin/ln "$@"
EOF
chmod +x "$WRAP/ismounted" "$WRAP/ln"

PATH="$WRAP:$PATH" TARGET_ROOT="$ROOT" \
  modules.d/30convertfs/convertfs.sh "$ROOT"
printf 'rc=%s\n' "$?"

ls -ld "$ROOT/bin" "$ROOT/bin.usrmove-old" \
  "$ROOT/usr/bin" "$ROOT/usr/bin.usrmove-old"
```

Observed exact-source failure:

```text
Create `.../bin' symlink.
Something failed. Move back to the original state
mv: cannot stat '.../bin': No such file or directory
rc=1

/bin                 MISSING
/bin.usrmove-old     present
/usr/bin             merged tree present
/usr/bin.usrmove-old present
```

The same exact source was then run with an `ln` wrapper that paused at the same handoff. A Python parent started the script in a new session and sent the selected signal to its process group after the wrapper created a marker showing that `ln` had been entered.

## Results

| Case | Exact-source exit | Cleanup message | Final `/bin` | `/bin.usrmove-old` | `/usr/bin.usrmove-old` |
| --- | ---: | --- | --- | --- | --- |
| normal | `0` | no | symlink to `usr/bin` | absent | absent |
| first `cp` fails | `42` | yes | original directory | absent | absent |
| root `ln` fails `42` | `1` | yes, then cleanup aborts | **missing** | present | present |
| SIGINT during root `ln` | `1` | yes, then cleanup aborts | **missing** | present | present |
| SIGTERM during root `ln` | terminated by 15 | no | **missing** | present | present |
| SIGHUP during root `ln` | terminated by 1 | no | **missing** | present | present |

For the injected `ln` failure and SIGINT cases, the distinguishing stderr line was:

```text
mv: cannot stat '.../bin': No such file or directory
```

That is the first rollback operation on the absent current path.

### Local candidate matrix

The two-part local candidate restored the original tree in every tested failure/interruption case:

| Case | Candidate exit | Final `/bin` | backup directories |
| --- | ---: | --- | --- |
| root `ln` fails `42` | `42` | original directory restored | absent |
| SIGINT during root `ln` | `1` | original directory restored | absent |
| SIGTERM during root `ln` | `143` | original directory restored | absent |
| SIGHUP during root `ln` | `129` | original directory restored | absent |

Both original marker files were present after candidate rollback in each case.

## Interpretation

### Demonstrated behavior

1. Current source has a rollback invariant mismatch at the root-directory handoff. A `.usrmove-old` backup can exist while the current path is intentionally absent, but `cleanup()` assumes the current path exists before restoring the backup.
2. `set -e` is still active when `cleanup()` runs. At the handoff failure point, the first cleanup `mv` fails and aborts the rollback before the saved original is restored.
3. This is not a generic inability to rollback. An early `cp` failure restores cleanly, which isolates the failure to the transition where the current path is absent.
4. Current SIGINT handling reaches rollback and then hits the same missing-current-path defect.
5. Current TERM/HUP handling does not enter rollback in the tested exact-source process-group cases, because only SIGINT has an explicit signal trap and the EXIT trap does not see a nonzero command status that would call `cleanup()`.
6. A small local candidate that removes the missing-current-path assumption and explicitly handles TERM/HUP restored the original tree across the tested matrix.

### Plausible consequence

An interrupted or failed usr-merge conversion can leave a core root path such as `/bin` absent while its original directory remains recoverable under `/bin.usrmove-old`. That state can disrupt later boot or rescue commands until manually repaired.

This consequence is plausible for the real initramfs path and directly demonstrated inside the disposable root fixture. The investigation did not boot a VM from the partially converted tree.

## Evidence boundary

Established:

- exact current GitHub source bytes for `convertfs.sh` at the resolved commit;
- normal exact-source conversion in a reduced disposable tree;
- clean rollback for an early injected `cp` failure;
- failed rollback for an injected root-`ln` failure;
- failed rollback for SIGINT at the same root handoff;
- skipped rollback for SIGTERM/SIGHUP at the same root handoff;
- successful rollback for all four cases with the local two-part candidate.

Outside this claim:

- no QEMU/initramfs boot was run;
- no real host root, mounted `/usr`, SELinux policy tree, separate filesystem, or package database was changed;
- only `bin` was populated in the fixture; sibling `sbin`, `lib`, and `lib64` use the same source loop but were not separately executed with failure injection;
- no fault was injected into `mv`, `rm`, `find`, or `ldconfig`;
- no candidate source branch, project test, CI run, release-specific package reproduction, or upstream packet was created;
- Bash versions other than 5.2.37 were not executed;
- conventional shell exit values for HUP/TERM were tested in the candidate, while true process-level signal identity remains an explicit design question.

Reopen or broaden the claim if another shell version changes trap/errexit behavior, a full initramfs run changes signal delivery semantics, sibling directories expose a different rollback owner, or project history shows a deliberate reason to leave a missing current path unrestored.

## Next step

Prepare a focused owned-fork candidate only after re-reading the target project's current contribution rules and refreshing the upstream base. The candidate should remain small:

1. make `cleanup()` restore `.usrmove-old` even when the current path is absent;
2. add a regression test that fails `ln` after the old root directory is moved aside and asserts complete restoration;
3. decide and test HUP/TERM behavior explicitly, including caller-visible exit semantics;
4. rerun the normal conversion and an early-failure negative control;
5. if practical, run the same discriminator through the real `rd.convertfs` initramfs hook in QEMU.

The root-`ln` failure alone is enough to justify the cleanup fix. Signal handling can be kept in the same candidate only if the project accepts the shared lifecycle boundary and exit-status policy; otherwise split it into a successor.

## Authority

No upstream issue, pull request, comment, review, email, patch submission, or other external interaction has been authorized or created. All source reads were read-only. All execution used disposable local fixtures. The candidate exists only as an uncommitted local experiment and was removed after the run.
