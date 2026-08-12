# nftables transaction/rollback scout — 2026-08-12

## TL;DR

This pass mapped the `LF-28` nftables atomic-update/rollback lane but did **not** promote a new investigation.

The source/history signal is real: nftables has repeatedly had userspace-cache and interactive-update defects where local state diverged from what a later command expected. In particular, the 2024 shell-test history records that tests for `nft -i` were added after reverting `e791dbe109b6` (`cache: recycle existing cache with incremental updates`), and nearby cache work fixed reset/list inconsistencies and anonymous-set crashes.

However, this runner does not currently have the `nft` executable installed, and direct access to the official Netfilter cgit log is partially protected by an interactive anti-bot challenge. Search-indexed official cgit pages are available, but that is not a strong enough current-source boundary for a new exact-head transaction claim.

**Disposition:** retain this as source orientation and stop. Reopen LF-28 when an exact nftables checkout plus executable is available in an isolated user+network namespace.

No upstream contact is authorized or has been made.

## Programme

`security-networking` / `LF-28` — nftables atomic update and rollback.

The programme status says nftables work should begin only after an isolated privileged-execution capability survey. This runner can create user/mount namespaces, but the nftables userspace executable is absent.

## Runner boundary

Observed locally:

```text
kernel: Linux 6.18.35 x86_64
uid: 0
outer Seccomp: 0
unshare: available
nft: not installed / not found in PATH
```

The missing executable means the central transaction invariant cannot be tested authoritatively here:

```text
baseline ruleset
-> submit one batch with an early valid change and a later failing change
-> require kernel ruleset unchanged
-> require userspace cache/output to match the unchanged kernel state
-> rerun a clean valid transaction
```

A source-only claim about rollback would leave the most important discriminator unexecuted.

## Official source orientation

Official Netfilter cgit material retrieved during this pass included:

- https://git.netfilter.org/nftables/tree/src/libnftables.c — `nft_netlink()` builds and sends a netlink batch, collects per-message errors, then resets the batch.
- https://git.netfilter.org/nftables/log/tests/shell/testcases — shell-test history containing cache and interactive-mode fixes.

A current indexed UAPI snapshot was also retrieved from official cgit, but direct log navigation currently returns the site's interactive Anubis challenge. Treat search-indexed source pages as orientation, not an exact-current checkout receipt.

## Historical signals worth carrying forward

The official shell-test log records several useful unknown-knowns for a future LF-28 execution pass:

### Interactive cache recycling was reverted

The test history says new `nft -i` shell coverage was added after issues led to reverting:

```text
e791dbe109b6 ("cache: recycle existing cache with incremental updates")
```

This makes long-lived/interactive cache reuse a high-value adjacent context whenever a transaction error is reproduced.

### Reset/list cache behavior has diverged before

A 2024 cache consolidation fixed an anonymous-set crash and documented inconsistencies between reset and list commands, including missing set elements in some reset output. The useful lesson is to compare the complete post-error cache/list view, not only the kernel batch return status.

### Incremental cache requirements are deliberately minimized

Nearby work relaxed cache requirements for rule replacement to avoid full-ruleset fetches. Future transaction tests should therefore classify whether a failure belongs to kernel batch atomicity or to a userspace cache level that was intentionally only partially populated.

## First executable probe when reopened

Use a disposable network namespace and exact nftables build.

### Batch atomicity

Start empty, then submit one file containing:

```text
add table inet lf
add chain inet lf c
<deliberately invalid command that is accepted by the parser but rejected by kernel/evaluation at the intended phase>
```

Distinguish parser/evaluation failure from a true kernel batch failure. For a kernel-batch test, the earlier table/chain must not survive if the transaction is rejected.

### Cache ownership

Immediately after the failed transaction, in the **same long-lived context when possible**:

```text
list ruleset
```

Compare that output against an independent fresh `nft list ruleset`. A stale userspace object after a rolled-back kernel transaction is a different defect from broken kernel atomicity.

### Clean rerun

Submit the valid prefix again without the failing command and require success. Inspect tables, chains, sets, handles, and any auto-generated objects relevant to the fixture.

### Adjacent contexts

Run the same discriminator through:

- one-shot `nft -f`;
- interactive `nft -i` or libnftables long-lived context;
- check mode `nft -c` as a no-publication control;
- a batch involving a set or map, because cache history shows these have different completeness requirements.

## Stop condition

Do not promote a defect from a parser rejection or a source-only suspicious cache mutation. Promote only when an exact build and isolated runtime show one of:

- a rejected kernel transaction leaves a partial kernel result;
- kernel rollback succeeds but the same userspace context retains stale objects;
- a clean rerun fails because state from the rejected transaction survives;
- check mode publishes state;
- output claims completion that disagrees with an independent fresh ruleset dump.

## Current disposition

- State: `SCOUTED / DEFERRED`
- Exact executable source head: unavailable in this runner
- Runtime nft executable: unavailable
- Useful retained history: interactive-cache revert and cache/reset/list fixes
- Cleanup state: no nftables or network state created
- Next safe action: reopen on a runner with exact nftables source + `nft` executable; execute batch atomicity and same-context cache controls before source candidate work
- External-contact state: no upstream interaction authorized or made
