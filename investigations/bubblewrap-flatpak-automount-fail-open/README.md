# Bubblewrap fail-open support exists, but current Flatpak cannot consume it yet

## TL;DR

Bubblewrap commit `2f55bae38468d0c50cf5df87b1e481e882b63acb` adds the reviewed `--not-a-security-boundary` mechanism needed to tolerate recursive submount remount failures for non-security uses such as Flatpak's `xdg-dbus-proxy` wrapper. The implementation is deliberately narrow: source mounts, destination setup, top-level remounts, namespace creation, `pivot_root`, capability dropping, and other fundamental failures still fail hard; only recursive child-mount flag-remount errors become warning-and-continue when the caller opts in.

At Flatpak commit `0baf60c3a11c0de6296dd7b21d5157f35df5cf69`, the exact `xdg-dbus-proxy` wrapper still does not pass this flag. That is not evidence of a missed one-line Flatpak fix: current Flatpak declares bubblewrap `>= 0.10.0` and its bundled fallback is bubblewrap 0.11.0 (`9ca3b05ec787acfb4b17bed37db5719fa777834f`), both predating the new option. Passing the option unconditionally would therefore break supported/bundled bubblewrap versions.

The current state is best described as a **version-gated downstream handoff**, not a newly demonstrated bubblewrap defect. The useful next question is how Flatpak wants to adopt the new behavior once it can either raise its bubblewrap floor or reliably feature-detect the option.

## Explain like I'm five

Flatpak starts a helper called `xdg-dbus-proxy` inside a small bubblewrap-made filesystem view. That helper view is for arranging files, not for keeping an attacker trapped.

An unreachable network automount under `/mnt`, `/var`, or another top-level directory can make bubblewrap fail while trying to copy mount safety flags to every nested mount. Bubblewrap now has a switch saying, roughly, “this particular wrapper is not a security wall, so warn and keep going if one nested mount cannot be remounted.”

Flatpak cannot simply add that switch today because it still promises to work with older bubblewrap versions that do not understand it.

## Why care

The long-running user-visible failure is broad: an unrelated unreachable automount can prevent Flatpak applications from launching because Flatpak waits for its D-Bus proxy wrapper, while that wrapper's bubblewrap process exits after a recursive mount-flag failure. Flatpak issue `#5112` and bubblewrap issue `#541` retain multiple reports across CIFS, NFS, SSHFS, `/mnt`, `/var/mnt`, and home-related paths.

The new bubblewrap option is directly aimed at this non-security wrapper class, but downstream version compatibility currently blocks straightforward adoption in Flatpak main.

## Current state

- State: `COMPLETE`
- Bubblewrap source head: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Flatpak source head: `0baf60c3a11c0de6296dd7b21d5157f35df5cf69`
- Flatpak bundled bubblewrap: `9ca3b05ec787acfb4b17bed37db5719fa777834f` (v0.11.0)
- Latest authoritative gate: source/history/review trace across both projects
- First incomplete step: runtime matrix with bubblewrap before/after the new option and a disposable failing automount
- Cleanup state: no runtime mounts, namespaces, automounts, or external systems changed
- Next safe action: revisit when Flatpak raises its bubblewrap floor, updates its bundled revision, or adds a reliable capability check; then test the proxy wrapper with a synthetic/disposable automount failure
- External-contact state: not authorized; no upstream issue, PR, comment, review, or email created

## Question

After bubblewrap added `--not-a-security-boundary`, is the long-standing Flatpak unreachable-automount launch failure now a bubblewrap implementation defect, or is the remaining boundary downstream adoption/version compatibility?

## Sources

### Bubblewrap

- Project: `containers/bubblewrap`
- Resolved commit: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Feature issue: https://github.com/containers/bubblewrap/issues/653
- Automount issue: https://github.com/containers/bubblewrap/issues/541
- Feature PR: https://github.com/containers/bubblewrap/pull/751
- Relevant files: `bind-mount.c`, `bind-mount.h`, `bubblewrap.c`, `bwrap.xml`, `tests/test-run.sh`

### Flatpak

- Project: `flatpak/flatpak`
- Resolved commit: `0baf60c3a11c0de6296dd7b21d5157f35df5cf69`
- Automount issue: https://github.com/flatpak/flatpak/issues/5112
- Relevant files: `common/flatpak-run-dbus.c`, `meson.build`, `subprojects/bubblewrap.wrap`

## Intent and history

Bubblewrap issue `#653` distinguishes two use cases:

1. a real sandbox where failures to enforce `ro`, `nosuid`, `nodev`, and similar properties must fail closed;
2. a namespace used only to adjust filesystem layout, where selected failures can safely warn and continue.

The issue explicitly names Flatpak's `xdg-dbus-proxy` wrapper and Steam Runtime as examples of the second category.

PR `#751` refined the implementation during review into two independent decisions:

- `bubblewrap.c` chooses which operation receives fail-open semantics;
- `bind-mount.c` chooses which internal bind-mount step may fail open.

Review also deliberately broadened the option from plain `--bind` to `--ro-bind` and `--dev-bind` when the whole invocation declares itself not a security boundary.

## Bubblewrap behavior at the pinned head

`setup_newroot()` builds bind flags for ordinary, read-only, and device bind operations. If `--not-a-security-boundary` was parsed, all three receive `BIND_FAIL_OPEN`.

`setup_op_bind_mount()` always requests a recursive bind.

Inside `bind_mount()`:

1. failure of the initial source bind remains fatal;
2. destination `realpath`, reopen, mountinfo lookup, and top-level flag remount remain fatal;
3. recursive child mounts are enumerated;
4. an `EACCES` child-remount failure was already ignored because the child is inaccessible to the wrapped user;
5. with `BIND_FAIL_OPEN`, other child-remount failures produce a warning and iteration continues;
6. without it, the same failure is returned to the caller and bubblewrap exits.

This boundary matches the merged documentation, which says fundamental sandbox setup operations still fail regardless of the new option.

## Why the automount report fits this mechanism

Bubblewrap issue `#541` and Flatpak issue `#5112` report failures such as:

```text
Can't bind mount /oldroot/mnt on /newroot/mnt:
Unable to apply mount flags: remount "/newroot/mnt/...": No such device
```

The reports become distinguishing when the automount is actively being triggered while bubblewrap starts. PR `#751` was tested against this family and its author reported the new option as a possible solution for that exact state.

Flatpak's own issue discussion explains why the failure appears during ordinary app launch: before starting the app, Flatpak creates a host-like namespace for `xdg-dbus-proxy`. It conservatively exposes top-level host directories because the helper executable or its libraries could live under nonstandard roots such as `/opt`, `/nix`, `/gnu`, or even a custom `/mnt/...` hierarchy. Recursive bind processing then encounters nested automounts.

## Flatpak source boundary

At `0baf60c3a11c0de6296dd7b21d5157f35df5cf69`, `common/flatpak-run-dbus.c:add_bwrap_wrapper()`:

- wraps `xdg-dbus-proxy` in bubblewrap;
- iterates host root entries;
- uses `O_PATH | O_NOFOLLOW` plus `fstatfs()` to skip a top-level entry when that entry itself is `AUTOFS_SUPER_MAGIC`;
- bind-mounts ordinary top-level directories, with `/tmp`, `/var`, and `/run` writable and most others read-only;
- does not pass `--not-a-security-boundary`.

Skipping only top-level autofs entries cannot avoid an automount nested below an ordinary top-level directory such as `/mnt/nas` or `/var/mnt/public`; bubblewrap's recursive remount traversal still sees those submounts.

## Why absence of the flag is not yet a demonstrated Flatpak defect

Flatpak's current build contract says:

```text
required_bwrap = '0.10.0'
```

and `subprojects/bubblewrap.wrap` pins:

```text
# v0.11.0
revision = 9ca3b05ec787acfb4b17bed37db5719fa777834f
```

The new bubblewrap feature landed later, after the project had already made a pre-release version bump toward 0.12.0. The bundled 0.11.0 source therefore cannot understand the option.

A Flatpak patch that always appends `--not-a-security-boundary` would violate its own supported dependency boundary and break its bundled fallback. Adoption needs an explicit version/capability decision rather than an unconditional argument addition.

A search of current Flatpak source found no `not-a-security-boundary` usage, and a targeted PR/commit search did not identify an existing adoption change. Search is orientation rather than proof that no work exists under different wording.

## Cross-context checks

### `--bind`, `--ro-bind`, and `--dev-bind`

The merged bubblewrap code applies fail-open to all three when the invocation opts out of being a security boundary. This matches review feedback and avoids a mode-specific hole where read-only or device binds would retain the old fatal child-remount behavior.

### Top-level versus nested mount

Fail-open begins at `mount_tab[1]`; the root of the newly created bind remains strict. Review explicitly considered this and concluded that a host mount directly below `/` becomes a child entry when `/` is recursively bound, while `/newroot` itself is not the problematic automount.

### Security sandbox versus helper wrapper

The new flag is caller-controlled and absent by default. Nothing in the merged change weakens normal bubblewrap sandbox invocations. Flatpak's actual application sandbox must continue failing closed where mount flags are security properties; the candidate consumer is specifically the non-security D-Bus proxy wrapper.

### Existing Flatpak top-level autofs avoidance

Flatpak already avoids binding a top-level root entry when `fstatfs()` identifies that entry itself as autofs. That is complementary, not sufficient: nested automounts below an otherwise ordinary root entry remain reachable by bubblewrap's recursive remount walk.

## Result

**Demonstrated from exact source:** bubblewrap now has a narrowly scoped mechanism that matches the failure owner identified in the old automount reports.

**Demonstrated from exact Flatpak source:** its D-Bus proxy wrapper is a named intended consumer but does not yet opt into the mechanism.

**Demonstrated compatibility boundary:** Flatpak still supports and bundles bubblewrap revisions that predate the option, so unconditional adoption would be incorrect.

**Negative result:** this pass did not find a new implementation error in bubblewrap's merged fail-open path. The remaining current-main gap is downstream version/capability handoff.

## Evidence boundary

No disposable automount was created and neither source tree was executed in this pass. The result is source/history/review based. It does not establish which future bubblewrap release first ships the option, which Linux distributions will package it, or which Flatpak release will adopt it.

It also does not claim that every Flatpak launch failure attributed to an unreachable mount is solved by this mechanism. Source-bind stalls, kernel automount behavior before the remount failure, application-sandbox paths that remain true security boundaries, and other mount-operation failures are separate contexts.

## Next step

Reopen this lane when one of these promotion signals appears:

- Flatpak raises `required_bwrap` to a revision/version containing the option;
- Flatpak updates its bundled bubblewrap past `9ca3b05...`;
- Flatpak gains a reliable runtime capability/version discriminator for the option;
- a report shows the exact same recursive child-remount failure still occurring in the non-security proxy wrapper **with** `--not-a-security-boundary` active.

At that point, run a four-cell disposable matrix:

```text
old bwrap + proxy wrapper
new bwrap + proxy wrapper without flag
new bwrap + proxy wrapper with flag
new bwrap + real security sandbox without flag
```

Assert process result, warning/failure identity, helper readiness, and the actual mount flags that survived on reachable and failing child mounts.

## Authority

No upstream contact is authorized or made. This is an internal Linux Fieldwork record.
