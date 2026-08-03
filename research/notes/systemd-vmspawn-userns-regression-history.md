# systemd-vmspawn ordinary-bind user namespace regression history

## Scope

This note records the introduction, intent, helper semantics, and candidate boundaries for `systemd/systemd#43141`. It supports the test carrier under `investigations/systemd-vmspawn-unmapped-bind-userns/` and does not contact the canonical project.

## Introduction

The issue bisects to commit:

`fd05c6c7593c5e36864d8784df91b878bbf991ab` — `vmspawn: Add support for foreign UID range owned directories`

That commit was part of PR `systemd/systemd#40415`, titled:

> Additions to nsresourced and vmspawn required for making use of the foreign UID range in mkosi

The PR merged on 2026-02-25. Its reviewed scope was foreign-UID ownership, uid translation, idmapped mounts, and related security constraints. It was not intended to require an ordinary unmapped bind to enter a new user namespace.

## Exact introduced control flow

The commit changed `start_virtiofsd()` so that:

1. `userns_fd` and `mapped_fd` begin invalid;
2. when `source_uid == FOREIGN_UID_MIN`, a child user namespace is allocated and an idmapped mount is prepared;
3. translated non-foreign ownership adds virtiofsd uid/gid translation options but does not allocate `userns_fd`;
4. ordinary binds with invalid source/target UID values also leave `userns_fd` invalid;
5. after fork, the child calls `namespace_enter(..., userns_fd, ...)` unconditionally.

Thus the new namespace operation was conditional in resource creation but unconditional in execution.

## Generic helper semantics

At canonical head `ac33190d1f66e870d511827cbed3ebeee2d704c2`, `namespace_enter()`:

1. calls `block_dlopen()`;
2. compares every supplied valid namespace fd with the current namespace and discards self references;
3. checks effective `CAP_SYS_ADMIN` even when every namespace and root fd is invalid;
4. if the caller lacks that capability and no child user namespace was supplied, returns `EPERM`;
5. otherwise enters requested namespaces and optionally changes root and uid/gid.

This is deliberate generic behavior. The helper accepts optional individual namespace descriptors, but it is not specified as a harmless no-op for an unprivileged caller that supplies no transition at all.

## Why caller-side repair is preferred

### Guard the actual transition

The narrow repair is:

```c
if (userns_fd >= 0) {
        r = namespace_enter(..., userns_fd, ...);
        if (r < 0)
                ...;
}
```

This matches resource ownership: only the path that allocated a child user namespace attempts to enter it.

### Do not weaken `namespace_enter()` globally

Changing the generic helper to return success whenever all descriptors are invalid could affect unrelated callers that rely on its privilege check, dlopen hardening, or error signaling. The vmspawn caller knows whether a transition exists and should express that condition.

### Do not pass the current user namespace

Passing a self user-namespace descriptor is not a substitute. `namespace_enter()` discards self namespace descriptors, then the unprivileged no-transition capability check still applies.

### Treat `block_dlopen()` separately

The helper blocks later dynamic loading before entering potentially hostile namespaces. On the ordinary-bind path, no namespace or root transition occurs before `invoke_callout_binary()` executes virtiofsd.

There is no reason to preserve an invalid namespace call solely for this side effect. If vmspawn has an independent policy that every callout child must block dlopen before exec, that should be expressed directly and consistently for all callouts, not accidentally through a failing helper invocation.

## Current path classification

| Path | `userns_fd` | Namespace entry expected |
|---|---:|---:|
| foreign UID range directory | valid child userns | yes |
| translated ordinary ownership | invalid | no |
| ordinary unmapped bind | invalid | no |
| root caller with ordinary bind | invalid | no transition, but current helper happens to pass capability check |
| unprivileged ordinary bind | invalid | current helper returns `EPERM` |

The root/unprivileged difference explains why the bug can remain hidden in privileged integration coverage.

## Regression contract

A complete test matrix should include:

1. unprivileged ordinary bind starts virtiofsd and reaches QEMU;
2. privileged ordinary bind remains working;
3. translated uid/gid path remains working without entering an unrelated user namespace;
4. foreign UID path still enters its allocated user namespace and moves the idmapped mount;
5. guest reads a host probe and creates a host-visible guest probe;
6. missing virtiofsd and unsupported QEMU device models remain correctly classified;
7. child cleanup after timeout or failure leaves no QEMU, virtiofsd, socket, or user unit residue.

## Test-carrier interpretation

The current controlled-fork test uses a blank raw disk and external timeout. It proves only the host-side startup boundary:

- baseline: immediate `EPERM` before virtiofsd exec;
- candidate: vmspawn reaches its long-running QEMU phase.

That test is intentionally cheaper than a guest-visible bind test. It should not replace the stronger second gate.

## Candidate review checklist

- guard only the namespace transition, not unrelated fd or mount setup;
- preserve `unshare(CLONE_NEWNS)` and `move_mount()` under their existing valid-fd conditions;
- preserve fd passing count: foreign path passes socket, userns, and mapped mount; ordinary path passes only socket;
- preserve parent-death signal and close-all-fds behavior;
- preserve virtiofsd uid/gid translation options;
- retain exact error logging on the path where namespace entry is genuinely required;
- add test before or with product code;
- compare privileged and unprivileged behavior.

## Evidence boundary

The source and history strongly support a caller-side descriptor guard. Runtime confirmation is still required. The test-only internal PR has no hosted run yet, and no product candidate has been labeled passing.

## Authority

No systemd issue comment, pull request, review, email, or other canonical-project interaction was created.
