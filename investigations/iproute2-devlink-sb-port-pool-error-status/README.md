# iproute2 devlink sb port-pool show masks receive errors

Date: 2026-08-12

Related programme lane: LF-29 — netlink compatibility and fallback.

## TL;DR

At current iproute2 head `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`, `cmd_sb_port_pool_show()` stores the result of `mnlu_gen_socket_sndrcv()` in `err`, closes the output section, and then returns `0` unconditionally. This can make a failed `devlink sb port pool show` operation report command success to scripts.

The neighboring `cmd_sb_show()`, `cmd_sb_pool_show()`, and `cmd_sb_tc_bind_show()` functions all return the receive result. The original shared-buffer implementation in 2016 also returned the receive result directly, so the current behavior is a regression from the original contract.

The smallest candidate is one line: `return err;`.

No upstream contact is authorized or has been made.

## Current source boundary

Project: `iproute2/iproute2`

Reviewed head: `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`

Current function:

```c
static int cmd_sb_port_pool_show(struct dl *dl)
{
    ...
    pr_out_section_start(dl, "port_pool");
    err = mnlu_gen_socket_sndrcv(&dl->nlg, nlh,
                                 cmd_sb_port_pool_show_cb, dl);
    pr_out_section_end(dl);
    return 0;
}
```

The callback itself can return `MNL_CB_ERROR` when required response attributes are absent, and `mnlu_gen_socket_sndrcv()` also carries kernel/netlink request failures. Both classes are therefore eligible to be hidden by the final `return 0`.

## Sibling control

Current neighboring show functions preserve the receive result:

- `cmd_sb_show()` -> `return err;`
- `cmd_sb_pool_show()` -> `return err;`
- `cmd_sb_tc_bind_show()` -> `return err;`

This makes `cmd_sb_port_pool_show()` the local outlier rather than a shared convention.

## History boundary

Shared-buffer support was introduced by:

- `e6d7367d795a41abeea4acc1af8f3885c8918ba7` — `devlink: implement shared buffer support`

At that introduction point the function ended with:

```c
return _mnlg_socket_sndrcv(dl->nlg, nlh, cmd_sb_port_pool_show_cb, dl);
```

So the original implementation propagated errors correctly.

The current incorrect behavior was introduced sometime after that point. The exact first-bad intermediate commit has not yet been pinned and should remain an explicit history subtask rather than being guessed.

The 2023 dump-selector conversion `70faecdca8f5187d2bc5ee95e4b6a01a50a2c916` changed argument parsing around this function but did not create the final `return 0`; the incorrect return was already present in its preimage.

## Reduced discriminator

Tracked fixture: `repro.c`.

It models only the return-value ownership boundary:

```text
recv=0    current=0 candidate=0
recv=-1   current=0 candidate=-1
recv=-22  current=0 candidate=-22
recv=-95  current=0 candidate=-95
```

This is intentionally smaller than an integration test because reproducing a real shared-buffer response requires suitable devlink hardware or a simulator. The source-level contract is nevertheless exact: a nonzero receive result is assigned to `err` and then discarded.

## Candidate

Tracked patch: `candidate.patch`.

```diff
- return 0;
+ return err;
```

This restores the original function behavior and matches all three neighboring shared-buffer show commands.

## Upstream duplicate search

Open and closed upstream issue searches for combinations of `sb port pool show`, `return success`, `error`, and `devlink` returned no matching report during this pass.

## Evidence boundary

Demonstrated:

- exact current source discards `mnlu_gen_socket_sndrcv()` return status;
- original 2016 source returned the receive status directly;
- neighboring current shared-buffer show commands return their receive errors;
- the repair is a one-line local return-value change;
- no upstream duplicate was found in the issue search performed during this pass.

Not yet demonstrated:

- exact first-bad intermediate commit;
- an exact-head binary integration run against real or simulated shared-buffer hardware;
- prevalence in ordinary user environments.

## Cleanup

No kernel, network namespace, link, mount, or hardware state was changed. The reduced fixture is pure process-local control flow.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. pin the first bad commit with file-history narrowing if the connector exposes enough history;
2. look for an existing devlink/netdevsim shared-buffer test surface that can force a receive error without special hardware;
3. continue auditing sibling command wrappers for swallowed receive errors.

External-contact state: no upstream interaction authorized or made.
