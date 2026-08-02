# systemd-vmspawn unmapped bind and user-namespace entry

## TL;DR

At canonical systemd commit `ac33190d1f66e870d511827cbed3ebeee2d704c2`, `start_virtiofsd()` still calls `namespace_enter()` even when an ordinary `--bind` operation has no user namespace to enter. For an unprivileged caller, `namespace_enter()` deliberately returns `EPERM` when both `CAP_SYS_ADMIN` and a child user-namespace descriptor are absent. The smallest likely repair is to enter a namespace only when `userns_fd` is valid, but that candidate is not yet runtime-tested and must preserve foreign-UID and translated-UID behavior.

## Explain like I'm five

A helper is told, “walk through this special door before starting.” For a normal shared folder, no special door was created. The helper still tries to walk through it and is rejected before it starts.

Literal example: ordinary user requests `--bind=/tmp/share` → vmspawn creates no helper user namespace → child calls `namespace_enter(..., -EBADF, ...)` → helper exits with `Operation not permitted` before virtiofsd runs.

## Why care

An unprivileged `systemd-vmspawn --user --bind=...` invocation cannot expose an ordinary host directory to the guest. The failure occurs before virtiofsd starts, so the guest never gets the requested filesystem and a normal user-visible feature regresses.

## Current state

- State: `SCOPING`
- Exact working head: canonical `ac33190d1f66e870d511827cbed3ebeee2d704c2`
- Latest authoritative gate or artifact: source-path review plus public issue reproducer and bisect
- First incomplete step: run the ordinary-user reproducer against the exact current head and record helper credentials/namespaces
- Cleanup state: no VM, namespace, mount, branch, or temporary runtime object created in this round
- Next safe action: create an exact-base branch in the controlled systemd fork and add a focused TEST-87 regression before changing product code
- External-contact state: none authorized or made

## Intent and precedent

Public issue `systemd/systemd#43141` reports an automated bisect to commit `fd05c6c7593c5e36864d8784df91b878bbf991ab`, `vmspawn: Add support for foreign UID range owned directories`.

That commit replaced the previous virtiofsd launch path with `pidref_safe_fork_full()`, optional user-namespace and mapped-mount descriptors, and a child-side `namespace_enter()` call. The new call was added unconditionally, while the immediately following mount-namespace `unshare()` was guarded by `userns_fd >= 0`.

Current `namespace_enter()` behavior is intentional in the general helper: when the caller lacks effective `CAP_SYS_ADMIN`, it requires a child user namespace before attempting other namespace changes. The vmspawn caller is responsible for not invoking that operation when it has no namespace transition to perform.

This investigation therefore treats the first distinguishing owner as the vmspawn call site, not `namespace_enter()`.

## Question

When vmspawn launches virtiofsd for an ordinary bind mount with no UID mapping, should it skip namespace entry while preserving the existing namespace and mount setup for foreign-UID directories?

## Source

- Project: systemd
- Requested revision: current canonical `main` observed 2026-08-03
- Resolved commit: `ac33190d1f66e870d511827cbed3ebeee2d704c2`
- Introducing commit identified by public bisect: `fd05c6c7593c5e36864d8784df91b878bbf991ab`
- Current `src/vmspawn/vmspawn.c` blob: `1e1283c3271d259e232462daf09113936ad3e314`
- Candidate source commit: none
- Controlled fork: `teamleaderleo/systemd`
- Local source path: not imported yet
- Import metadata: not present

## Environment

- Distribution and release: not executed in this round
- Kernel and architecture: issue reproducer reports Linux x86-64; exact local execution environment remains to be recorded
- Shell: proposed TEST-87 fixture uses Bash
- Privileges: ordinary user, no `sudo`, no effective `CAP_SYS_ADMIN`
- Context: direct-boot VM with QEMU and virtiofsd
- Relevant tool versions: record systemd build, QEMU, virtiofsd, kernel, Meson, and Ninja at execution time

## Baseline behavior

The current child path performs:

1. initialize `userns_fd` and `mapped_fd` to invalid descriptors;
2. allocate a user namespace only for the foreign UID range case;
3. fork the virtiofsd child;
4. call `namespace_enter()` unconditionally with `userns_fd`;
5. unshare a mount namespace only when `userns_fd >= 0`;
6. move the mapped mount only when `mapped_fd >= 0`;
7. execute virtiofsd.

`namespace_enter()` checks effective `CAP_SYS_ADMIN`. Without that capability and without a valid user namespace descriptor, it returns synthetic `EPERM` before any `setns()` call.

For a regular runtime bind, the public issue records both source and target UIDs as invalid and therefore no user namespace descriptor. The ordinary-user child takes the exact rejecting branch above.

## Hypothesis or candidate

### Primary candidate

Guard `namespace_enter()` with `userns_fd >= 0`, matching the existing guard around `unshare(CLONE_NEWNS)`.

The candidate should:

- accept a regular unmapped bind from an ordinary user;
- preserve the foreign-UID path that allocates a child user namespace and moves an idmapped mount;
- preserve translated UID/GID arguments passed to virtiofsd;
- preserve socket descriptor inheritance and close-on-exec handling;
- leave general `namespace_enter()` capability enforcement unchanged.

### Important control

Do not replace the call with a general “ignore EPERM” fallback. A valid namespace transition that fails with `EPERM` is materially different from having no namespace descriptor. The descriptor state is the discriminator.

### Open credential question

Skipping `namespace_enter()` also skips its `block_dlopen()` call and its conditional `reset_uid_gid()` path. With no user namespace descriptor, the latter would not run anyway; the former is a defense used before switching namespace/root context. Confirm whether the vmspawn child should independently block late `dlopen()` before executing virtiofsd, rather than relying on a no-op namespace call for that side effect.

## Reproduction

Proposed exact-current-head baseline:

```sh
meson setup build -Dmode=developer -Dtests=false
ninja -C build systemd-vmspawn

share=$(mktemp -d)
printf '%s\n' vmspawn-bind-ok >"$share/host-probe"

build/systemd-vmspawn \
    --user \
    --register=no \
    --image=/path/to/linux.raw \
    --linux=/path/to/vmlinuz \
    --bind="$share" \
    root=PARTLABEL=root-x86-64 \
    rootfstype=ext4 \
    rootwait rw
```

The retained integration fixture should be self-contained beside the existing TEST-87 vmspawn tests:

1. create a minimal direct-boot guest;
2. create a host share with `host-probe`;
3. run vmspawn as a non-root account with `--user --register=no --bind=`;
4. have the guest verify `host-probe` and create `guest-probe`;
5. verify `guest-probe` on the host;
6. capture ownership and mode of both files;
7. terminate the VM and prove the virtiofsd child and runtime directory are gone.

## Results

### Demonstrated by source review

- The current vmspawn child calls `namespace_enter()` with an invalid `userns_fd` in the no-userns path.
- `namespace_enter()` rejects an unprivileged caller that has neither `CAP_SYS_ADMIN` nor a child user namespace.
- The subsequent mount-namespace and mapped-mount operations are already conditional on valid descriptors.
- The introducing commit is the same commit identified by the public issue's automated bisect.
- No competing pull request matching issue 43141 or the exact failure terms was found during this round.

### Not yet demonstrated here

- A local current-head failure transcript.
- Candidate success under the same VM image and kernel.
- Foreign-UID and explicit UID-translation regression results.
- Whether a no-userns helper needs an independent `block_dlopen()` call.

## Interpretation

The source control flow agrees with the public reproducer and bisect. The strongest current explanation is a call-site precondition error: vmspawn invokes a namespace-entry helper in a path where no namespace transition exists.

A descriptor guard is a narrower candidate than weakening `namespace_enter()`, because the general helper's capability check protects real namespace transitions elsewhere in systemd.

This is a source-supported candidate, not yet an executed fix.

## Cross-context review

| Context | Discriminator | Why it could change the decision |
|---|---|---|
| Ordinary `--bind` | both UID fields invalid; no userns fd | headline failing path |
| Foreign UID directory | userns and mapped-mount fds valid | must keep namespace entry and move-mount behavior |
| Explicit UID translation | translate arguments present, possibly no userns fd | determines whether translation alone needs namespace entry |
| `--directory` root | source UID derived from directory owner | may follow a different authority contract from runtime bind |
| Root/system scope | effective `CAP_SYS_ADMIN` may hide the bug | negative control; success as root does not validate ordinary-user behavior |
| Helper hardening | `block_dlopen()` side effect | may justify a separate explicit hardening call, not an invalid namespace operation |

Stop widening this candidate when the valid-descriptor guard explains all call-site variants. Split any helper-hardening question into a separate change.

## Evidence boundary

This record is based on exact public source, issue text, introducing history, and existing test harness review. It does not claim that a patch builds or that a VM test passes. No privileged execution, full systemd test suite, QEMU launch, or virtiofsd launch was performed in this round.

## Next step

Create a canonical-base branch in `teamleaderleo/systemd`, add the ordinary-user TEST-87 regression first, and capture the baseline failure. Then apply the descriptor guard and rerun:

- ordinary unmapped bind;
- foreign-UID path where available;
- explicit UID translation;
- syntax/build checks and the focused TEST-87 target.

## Authority

No upstream issue, pull request, comment, email, review, or other external interaction has been authorized or made.