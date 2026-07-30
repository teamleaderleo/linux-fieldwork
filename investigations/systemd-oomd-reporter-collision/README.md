# systemd-oomd reporter collision across user-manager reload

Tracking: issue #140, upstream systemd issue #43174, and issue #194 follow-on work.

## TL;DR

A continuously running `user@<uid>.service` can disappear from systemd-oomd's monitored set after that user's manager executes `daemon-reload`.

Current systemd source supports a precise mechanism:

1. PID 1 reports `user@<uid>.service` with `ManagedOOMMemoryPressure=kill`;
2. the user manager's root `-.slice` names the same kernel cgroup path;
3. unit reload republishes the user manager root with its default `auto` policy;
4. oomd stores one context per **path**, not one subscription per reporter;
5. an `auto` message removes that path, including PID 1's stronger registration;
6. PID 1 sees no unit transition and therefore does not send a replacement `kill` update.

This is a source-supported mechanism and a strong match for the public reproducer. It is not yet a current-main VM execution result.

## Explain like I'm five

Imagine a coat-check room with one hook labelled:

```text
/user.slice/user-1000.slice/user@1000.service
```

Two clerks use the same hook:

- the building clerk, PID 1, hangs a red card saying **protect this group**;
- the user's clerk later reloads its notebook and says **I have no special instruction for my root group**.

The coat-check system remembers only the hook label. It does not remember which clerk attached which card.

So the second clerk's “nothing special” message removes the first clerk's protection card.

The service never stopped. The cgroup never vanished. The protection record was simply overwritten by a different reporter that happened to use the same pathname.

## Why care

This is not merely a stale display entry. `user@<uid>.service` is the monitored ancestor that makes ordinary user services eligible for memory-pressure action when those descendants use the default `ManagedOOMMemoryPressure=auto` behavior.

After the collision:

- `systemd-oomd.service` remains active;
- its bus and sockets remain healthy;
- `oomctl` may still show user scopes;
- the affected `user@<uid>.service` continues running;
- its unit property still says `kill`;
- but the ancestor is absent from oomd's monitored map.

That is a dangerous failure shape because the guardrail looks healthy while silently losing coverage.

## Demonstrated source chain

Pinned systemd revision:

```text
6d7a2ec6ba21184cac1cfd39fe50d0def23220f2
```

### 1. The user manager discovers its own cgroup root

`src/core/cgroup.c` initializes `m->cgroup_root` using the current manager process:

```c
r = cg_pid_get_path(0, &m->cgroup_root);
```

For the user manager, that is the cgroup in which `user@<uid>.service` placed it.

### 2. The user manager root slice reuses that exact path

The root `-.slice` does not create a child path:

```c
if (unit_has_name(u, SPECIAL_ROOT_SLICE))
        p = strdup(u->manager->cgroup_root);
```

Therefore the user manager's `-.slice` and PID 1's `user@<uid>.service` can describe the same kernel cgroup through different unit identities.

### 3. The default ManagedOOM mode is `auto`

A fresh cgroup context initializes both ManagedOOM modes to `MANAGED_OOM_AUTO`.

### 4. Unit loading publishes ManagedOOM state

At the end of unit load, `src/core/unit.c` calls:

```c
(void) manager_varlink_send_managed_oom_update(u);
```

The same send path is also used for relevant active-state transitions.

### 5. User-manager updates include `auto`

`src/core/varlink.c` builds all ManagedOOM property entries for an update. In user mode it sends them directly to oomd using `ReportManagedOOMCGroups`.

The initial user-manager connection filters for explicitly enabled policies, but ordinary per-unit updates do not apply that initial-call filter. An active root slice with the default policy can therefore publish `auto` for the shared path.

### 6. Oomd deletes by path, without reporter identity

`src/oom/oomd-manager.c` chooses a monitored hashmap by property. For `auto`, it performs:

```c
hashmap_remove(monitor_hm, empty_to_root(message.path))
```

`OomdCGroupContext` stores the path and effective thresholds, but not the reporting manager or connection. The hashmap contract is explicitly path to context.

The peer UID is used to validate whether a non-root sender owns the cgroup. It is not retained as subscription identity.

## Inference

The source facts above support this sequence:

```text
PID 1:          path P → kill, limit 50%
user manager:   reloads root -.slice
user manager:   path P → auto
systemd-oomd:   remove path P
PID 1:          no service state/property transition
result:         path P remains unmonitored
```

This inference explains all important observations in upstream issue #43174:

- only the PID-1 registration is lost;
- the service remains active and never restarts;
- the cgroup path still exists;
- user-manager-owned child scopes continue to register;
- restarting oomd restores the PID-1 snapshot until the next user reload;
- no disconnect or cgroup-deletion error is required.

## Was this intentional?

The individual behaviors are intentional:

- PID 1 reports system-unit ManagedOOM policy;
- user managers may report cgroups they own;
- `auto` means stop monitoring that unit/property;
- hashmap lookup by cgroup path is efficient because oomd ultimately acts on cgroups.

The accidental design assumption is that one cgroup path has one authoritative reporter. The user-manager root violates that assumption: two managers attach different unit identities and policies to the same kernel object.

## Retained regression

`0001-test-preserve-system-registration-across-user-reload.patch` adds a focused case to `test/units/TEST-55-OOMD.sh`:

1. configure `user@.service` with memory-pressure `kill` and a 50% limit;
2. start a lingering test user's manager;
3. wait until the exact `user@<uid>.service` cgroup appears in `oomctl`;
4. record its active timestamp;
5. execute `systemctl --machine testuser@.host --user daemon-reload`;
6. check the exact cgroup remains monitored after 1, 5, and 10 seconds;
7. prove `ActiveEnterTimestampMonotonic` is unchanged, `NRestarts=0`, and the system-unit property remains `kill`.

The time-separated checks reject both immediate loss and a false transient recovery. The identity controls prove that a service restart did not merely repopulate oomd.

## Fix designs

### A. Track subscriptions per reporter, then derive effective policy

Preferred architectural direction.

Store contributions separately, for example by:

```text
(property, cgroup path, reporter identity)
```

Then calculate one effective monitored context for the cgroup. An `auto` update removes only that reporter's contribution.

The reporter identity needs to survive reconnection and distinguish at least PID 1 from each user manager. A raw connection pointer alone is not a durable policy identity.

Open policy questions remain:

- when two reporters request different pressure limits, should oomd choose the stricter, the more authoritative, or reject ambiguity;
- whether PID 1 should always outrank a user manager for the user-manager root;
- how to remove a reporter's subscriptions on disconnect without deleting another reporter's contribution;
- how dump output should expose overlapping sources.

### B. Give PID 1 precedence for an identical path

A narrower correction could refuse a non-root `auto` unsubscribe when a root reporter still requests `kill` for the same path.

This likely fixes the reported case, but it embeds precedence rules into the receive path and still needs source tracking to know whether root currently contributes policy.

### C. Suppress user-root `auto` publication

The user manager could avoid publishing default `auto` for its root `-.slice`.

This is small, but it treats one collision symptom rather than the shared-path subscription model. It may also prevent a user manager from legitimately withdrawing a policy that it previously supplied for its root.

### D. Re-send PID 1 policy after every user reload

Not a sound boundary. PID 1 does not necessarily know that a nested user manager reloaded, and periodic reassertion would turn deterministic ownership into a race.

## Current recommended direction

First land the regression and demonstrate it on current systemd main. Then implement source-aware subscriptions with an explicit effective-policy rule. A narrow PID-1 precedence patch is acceptable only if the project deliberately chooses that policy and tests conflicting limits, disconnects, resubscription, and root/user `auto` transitions.

## Evidence boundary

`verify_source.py` proves that the exact pinned source contains every link required by the collision mechanism and emits a machine-readable record. The focused workflow also proves that the regression patch applies cleanly and leaves the complete OOMD integration test as valid shell.

Those checks do **not** execute systemd, Varlink, cgroup v2, pressure stall information, a user manager, or oomd. A disposable VM run of the patched `TEST-55-OOMD.sh` remains required before calling the runtime defect reproduced on current main.

The upstream issue reports runtime reproductions on systemd 261 and 259. Linux Fieldwork has not independently reproduced those machines in this branch.

## Disposition

`SOURCE MECHANISM CONFIRMED — HOLD FOR CURRENT-MAIN VM REGRESSION AND PRODUCT DESIGN`.

Human decisions:

1. accept or reject source-aware per-reporter subscriptions as the product direction;
2. define effective policy when reporters overlap;
3. authorize a current-main VM build and test slice;
4. separately authorize any upstream comment or pull request.

## Authority

Internal Linux Fieldwork research only. Public source and issue reading are authorized. No systemd issue comment, pull request, review, patch submission, email, or other external contact is included or authorized.
