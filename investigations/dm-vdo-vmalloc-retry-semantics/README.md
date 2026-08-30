# `dm-vdo` loses its no-OOM retry modifier on Linux 7.0 `vmalloc`

## In simple words

Linux v7.0 makes `dm-vdo`'s large startup allocation mean something weaker than
the VDO source says. VDO asks `__vmalloc()` to retry reclaim but fail instead of
invoking the OOM killer. This kernel rejects that retry modifier, warns once,
removes it, and proceeds with ordinary `GFP_KERNEL` reclaim semantics.

```text
dm-vdo asks for GFP_KERNEL | __GFP_RETRY_MAYFAIL
                              |
Linux 7.0 vmalloc rejects ----+
                              v
warn once -> remove retry modifier -> allocate with GFP_KERNEL
```

Big Red observed exactly that fixup while creating an owned VDO experiment.
The allocation succeeded and the VDO target started; no corruption, allocation
failure, or OOM was observed. The practical defect is the lost failure
contract under memory pressure, not failure of the successful experiment.

Current upstream Linux already contains the core fix: commit
[`3caedb3b99ea`](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=3caedb3b99eabe9f67b7b6c704ab8a92fe35dcec)
adds bounded `vmalloc` support for `__GFP_RETRY_MAYFAIL` and
`__GFP_NORETRY`. Big Red's current Ubuntu package candidate remains
`7.0.0-30.30`, which does not contain that support. VDO is not Big Red's
selected interactive storage path and no live VDO mapping remains, so the host
decision is to make no kernel, module, or storage change from this warning.

## Current state

- State: `COMPLETE`
- Exact working head: recorded by Linux Fieldwork PR for issue
  [#700](https://github.com/teamleaderleo/linux-fieldwork/issues/700)
- Latest authoritative evidence: one exact live trace plus exact Ubuntu,
  Linux v7.0, and current-main source comparison
- First incomplete step: none inside the bounded disposition
- Cleanup state: no VDO device, LVM volume, experimental loop device, mount,
  probe, worker, or temporary source checkout remains
- Next safe action: accept the ordinary Ubuntu kernel stream; recheck source
  only when its candidate changes
- External-contact state: no upstream contact authorized or made

## Intent and source history

The exact Ubuntu VDO source at tag `Ubuntu-7.0.0-30.30` defines:

```c
const gfp_t gfp_flags =
    GFP_KERNEL | __GFP_ZERO | __GFP_RETRY_MAYFAIL;
```

Its comment says the modifier permits a definite but longer reclaim effort,
does not directly trigger the OOM killer, and lets VDO fail its higher-level
request instead. Requests larger than one page reach repeated `__vmalloc()`
calls with those flags and, normally, `__GFP_NOWARN`.

Linux v7.0 commit `028ef9c96e96197026887c0f092424679298aae8` contains two
relevant facts in `mm/vmalloc.c`:

1. `GFP_VMALLOC_SUPPORTED` excludes `__GFP_RETRY_MAYFAIL`.
2. The API documentation explicitly says both `__GFP_RETRY_MAYFAIL` and
   `__GFP_NORETRY` are unsupported.

The invalid-flag path masks unsupported bits and uses `WARN_ONCE`. The warning
is therefore a sentinel for the mismatch, not a count of affected VDO
allocations during the boot.

Upstream commit `3caedb3b99eabe9f67b7b6c704ab8a92fe35dcec` changes the
owner that can preserve the contract:

- both modifiers enter `GFP_VMALLOC_SUPPORTED`;
- `memalloc_apply_gfp_scope()` applies `memalloc_noreclaim_save()` for them,
  preventing OOM-killer recursion from page-table allocation;
- the documentation states the limitation: page tables use NOWAIT semantics
  and can fail under moderate memory pressure.

That commit is not in v7.0 and is an ancestor of inspected current upstream
main `08dbfad3f5040f5bdb6c529da20d6d4e81fefd72`. The current `dm-vdo`
call therefore becomes valid without a VDO-specific workaround.

Primary source boundaries:

- [Ubuntu `7.0.0-30.30` `mm/vmalloc.c`](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/resolute/tree/mm/vmalloc.c?h=Ubuntu-7.0.0-30.30)
- [Ubuntu `7.0.0-30.30` `dm-vdo/memory-alloc.c`](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/resolute/tree/drivers/md/dm-vdo/memory-alloc.c?h=Ubuntu-7.0.0-30.30)
- [Linux v7.0 `mm/vmalloc.c`](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/vmalloc.c?h=v7.0)
- [Linux v7.0 `dm-vdo/memory-alloc.c`](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/md/dm-vdo/memory-alloc.c?h=v7.0)
- [upstream support commit](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=3caedb3b99eabe9f67b7b6c704ab8a92fe35dcec)

## Exact Big Red observation

Environment:

- Ubuntu 26.04.1 (`resolute`), x86-64
- kernel `7.0.0-30-generic`, package `7.0.0-30.30`
- kernel version signature based on upstream `7.0.12`
- `dm-vdo` module from the matching Ubuntu kernel package
- VDO userspace `8.3.1.1`
- privileged, route-owned XFS/reflink/VDO performance experiment

At `2026-08-29 19:36:25 Asia/Shanghai`, VDO constructed an 18-thread
compression-only target. The kernel emitted:

```text
Unexpected gfp: 0x4000 (__GFP_RETRY_MAYFAIL).
Fixing up to gfp: 0x2dc0 (GFP_KERNEL|__GFP_ZERO|__GFP_NOWARN).
```

The stack bound the warning to:

```text
__vmalloc_noprof
vdo_allocate_memory [dm_vdo]
vdo_make [dm_vdo]
vdo_initialize [dm_vdo]
construct_new_vdo [dm_vdo]
vdo_ctr [dm_vdo]
```

Less than 60 milliseconds later, the same target logged normal operation,
started, and resumed. The retained experiment later completed its workload
and removed the target cleanly. The current host reports no VDO device or LVM
volume; `dm_vdo` remains loaded with use count zero.

Exactly one matching warning exists in the current boot. Because the source
uses `WARN_ONCE`, that count cannot establish the number of later fixups.

## Adjacent-context matrix

| Context | Discriminator | Result | Decision effect |
|---|---|---|---|
| VDO request at or below one page | `use_kmalloc(size)` | `kmalloc()` receives the modifier; this `vmalloc` mask is not involved | Do not claim all VDO allocations lose the modifier |
| VDO request above one page on Ubuntu `7.0.0-30.30` | live stack plus exact mask | `__vmalloc()` strips the modifier and warns once | Confirms the observed contract mismatch |
| Same successful target | target start and later clean experiment completion | no demonstrated allocation failure, OOM, or corruption | Keep the consequence limited to failure semantics under pressure |
| Current upstream `vmalloc` | exact support commit and current-main ancestry | accepts the modifier and applies a noreclaim scope | Core upstream already owns the repair; no VDO patch is selected |
| Current Ubuntu package candidate | `apt-cache policy linux-image-generic` | still `7.0.0-30.30` | There is no ordinary Big Red package update to test yet |
| Current Big Red storage state | `dmsetup`, LVM inventory, module use count | no VDO device or volume; module use count zero | No live mitigation or kernel replacement is justified |

## Reproduction and source checks

The live event should not be manufactured again. The retained current-boot
trace is sufficient. These read-only commands recover the relevant boundaries:

```sh
uname -a
dpkg-query -W 'linux-image-7.0.0-30-generic'
apt-cache policy linux-image-generic

journalctl -b -k --since '2026-08-29 19:36:20' \
  --until '2026-08-29 19:36:27' --no-pager

git ls-remote --tags https://github.com/torvalds/linux.git 'v7.0^{}'

sudo -n dmsetup ls --target vdo
sudo -n vgs --noheadings -o vg_name
sudo -n lvs --noheadings -o vg_name,lv_name,segtype
lsmod | grep '^dm_vdo'
```

The source comparison inspected the exact Ubuntu tag via Launchpad, Linux
v7.0 and current main via the official kernel repository, and the complete
upstream support commit. No source was executed and no module was rebuilt.

## Interpretation

This is a bounded integration window between two upstream changes:

1. Linux began warning and masking unsupported `vmalloc` GFP flags.
2. Later Linux gained an approximation of the no-OOM retry semantics VDO had
   already requested.

During that window VDO's large allocations continue, but their retry modifier
is removed. The warning correctly identifies a real semantic mismatch. It is
not evidence that Big Red's NVMe, XFS, LVM, or VDO data was corrupt, and it is
not a reason to suppress the warning.

The smallest current repair owner is the already-merged `vmalloc` support
commit. Replacing `__GFP_RETRY_MAYFAIL` inside VDO would either abandon its
stated failure contract or reimplement memory-management behavior at the
wrong layer. Big Red should not install a custom kernel merely to improve a
storage treatment already rejected for interactive latency.

## Evidence boundary and reopen rule

This record does not execute a memory-pressure/OOM fixture, prove the exact
amount of memory affected, validate an Ubuntu backport, or compare every
architecture. The successful target proves only the observed allocation path;
it does not prove that stripping the modifier is harmless under pressure.

Reopen when one of these changes:

- Ubuntu publishes a new installed candidate and its exact source relation to
  `3caedb3b...` needs classification;
- a VDO target on a kernel containing that commit still emits the same invalid
  GFP warning;
- VDO changes its allocation contract or stops using the modifier;
- Big Red deliberately selects VDO for a live storage role, which would require
  a separate safety and performance decision.

Do not create a VDO target, induce memory pressure, reload `dm_vdo`, change the
kernel, or alter host storage merely to reopen this source-complete result.

## Verification and cleanup

- `git diff --check` passed.
- Python compilation of the repository tools and tests passed.
- The repository runner retained its expected 445 of 468 discovered tests.
  It passed 443 and failed two unrelated caching-proxy publication timing
  tests.
- A fresh detached worktree at untouched `origin/main`
  `0e2ac8c981ddb593aaf29f6d2f92e4758d4bbdc1` reproduced the same two
  failures with the same zero-byte/empty-temporary observations. This record
  changed only Markdown and did not cause that baseline failure class.
- The detached baseline worktree and its generated bytecode were removed.
  No proxy process or test listener survived.
- No experimental block device, VDO mapping, LVM volume, mount, loop device,
  memory-pressure worker, source build, module reload, package change, or
  kernel change was created by this investigation.

## Authority

All activity stayed within owned Linux Fieldwork, read-only primary-source
inspection, and the already-retained Big Red experiment trace. No upstream
issue, email, patch submission, pull request, comment, review, reaction, or
other third-party interaction was authorized or created.
