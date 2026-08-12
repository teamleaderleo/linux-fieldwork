# Propagation-mode expansion

Date: 2026-08-12

Tracking: `teamleaderleo/linux-fieldwork#602`

## TL;DR

The stale-pre-overmount-fd discriminator was repeated for three propagation transitions. In every case, applying the legacy propagation operation through `/proc/self/fd/<old_fd>` changed the hidden lower mount while the visible overmount retained its original state. Applying the same operation through the reopened post-overmount fd then changed the visible mount.

This extends the original `MS_PRIVATE` result to `MS_UNBINDABLE` and `MS_SLAVE`. The defect mechanism is therefore the target mount identity, not one propagation flag's semantics.

## Environment

Same disposable runtime class as the primary investigation:

- Linux 6.18.35 x86_64
- Python 3.13.5
- user + mount namespace via `unshare -Urnm`
- `/` made recursively private before fixture creation
- namespace exit owned cleanup

## Private

Observed:

```text
private before 95 shared:1 96 shared:2
private stale 95 private 96 shared:2
private control 95 private 96 private
```

Interpretation:

- hidden old mount ID 95 began in shared peer group 1;
- visible new mount ID 96 began in shared peer group 2;
- stale-fd operation changed only mount 95 to private;
- reopened-fd control then changed mount 96 to private.

## Unbindable

Observed:

```text
unbindable before 97 shared:1 98 shared:2
unbindable stale 97 unbindable 98 shared:2
unbindable control 97 unbindable 98 unbindable
```

The same identity split holds. The stale fd made only hidden mount 97 unbindable; visible mount 98 remained shared until the reopened-fd control.

## Slave

For the slave control, the lower source was shared before the bind fixture was constructed. This gave the transition a visible `master:` relationship rather than reducing it to a private mount.

Observed:

```text
slave before 100 shared:1 101 shared:2
slave stale 100 master:1 101 shared:2
slave control 100 master:1 101 master:2
```

Again the stale path changed only the hidden mount. Mount 100 became a slave of peer group 1 while visible mount 101 stayed shared. The reopened-fd control then changed mount 101 into a slave of peer group 2.

## Result

The tested propagation modes now establish the same invariant failure:

```text
pre-overmount fd -> hidden lower mount
reopened fd      -> visible top mount
```

A propagation fallback that uses a proc-fd pathname derived from the pre-overmount fd can report success while applying the requested state to the wrong mount object.

The candidate boundary remains small: once current crun reopens `targetfd` after the overmount, refresh the fd-derived `real_target` pathname before any later legacy fallback can use it.

## Evidence boundary

Demonstrated here:

- `MS_PRIVATE` wrong-object selection;
- `MS_UNBINDABLE` wrong-object selection;
- `MS_SLAVE` wrong-object selection with a visible master relationship;
- reopened-fd controls for all three modes.

Still pending:

- `MS_SHARED` as the requested transition from a non-shared starting state;
- compiled crun execution;
- forced `mount_setattr()` failure inside crun itself;
- candidate test-suite execution.

No upstream contact is authorized or made.
