# iproute2 devlink DPIPE primary request errors report success

Date: 2026-08-12

Related programme lane: LF-29 — netlink compatibility and error ownership.

## TL;DR

At current iproute2 head `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`, two DPIPE command paths discard the status of the request that actually defines the command result:

1. `devlink dpipe table show` sends `DEVLINK_CMD_DPIPE_TABLE_GET` but does not store or return `mnlu_gen_socket_sndrcv()`'s result, then returns `0`.
2. `devlink dpipe table dump` sends `DEVLINK_CMD_DPIPE_ENTRIES_GET` but does not store its result, then returns the stale `err` from the earlier header query (normally `0`).

Both callback paths can return `MNL_CB_ERROR`, and the receive helper also carries kernel/netlink errors, so a failed primary query can be presented to scripts as command success.

This behavior is longstanding: the same discarded primary receives are present in the 2017 DPIPE introduction. It should therefore be described as a longstanding command-status defect, not a newly introduced regression.

No upstream contact is authorized or has been made.

## Exact source boundary

Project: `iproute2/iproute2`

Reviewed head: `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`

Current `cmd_dpipe_table_show()` performs several stages:

1. fetch headers — fatal on error;
2. fetch resources — intentionally optional/nonfatal;
3. fetch DPIPE tables — primary command result, currently ignored.

The current final stage is effectively:

```c
pr_out_section_start(dl, "table");
mnlu_gen_socket_sndrcv(&dl->nlg, nlh,
                       cmd_dpipe_table_show_cb, &dpipe_ctx);
pr_out_section_end(dl);
...
return 0;
```

Current `cmd_dpipe_table_dump()` first gets headers, checks that result, then performs the primary entry request without assigning its return value:

```c
pr_out_section_start(dl, "table_entry");
mnlu_gen_socket_sndrcv(&dl->nlg, nlh,
                       cmd_dpipe_table_entry_dump_cb, &ctx);
pr_out_section_end(dl);
out:
    ...
    return err;
```

At that point `err` still describes the prior header stage.

## Callback error boundary

The table callback returns `MNL_CB_ERROR` when the response is missing required handle/table attributes or when nested table parsing fails.

The entries callback returns `MNL_CB_ERROR` when required attributes are absent or nested entry parsing fails.

Therefore the discarded receive result is not merely a transport-status detail: it also owns userspace response-validation failures.

## History boundary

DPIPE support was introduced by:

- `153c1a9b21e5b7b78e066de2b93a4edb8c3dc498` — `devlink: Add support for pipeline debug (dpipe)`

The introduction already contains the same pattern for both table show and entry dump: call the receive helper without capturing the result and later return an earlier `err` value.

So no first-bad regression commit is claimed.

### Important intentional nonfatal control

Commit `0e7e1819453cc5bc5610c896d3cbc5a30b48b164` (`devlink: relax dpipe table show dependency on resources`) explicitly made *resource retrieval* nonfatal because resource data is only additional information in DPIPE table output.

That is a useful control for the candidate design. The candidate does **not** make resource-query failures fatal. It overwrites the optional resource result with the subsequent primary `DPIPE_TABLE_GET` result, so:

- resource fails, primary table succeeds -> command succeeds;
- primary table fails -> command fails.

This preserves the documented 2019 relaxation.

## Reduced discriminator

Tracked fixture: `repro.c`.

Expected model output:

```text
show optional-resource-fail primary-ok: current=0 candidate=0
show optional-resource-fail primary-fail: current=0 candidate=-22
show resource-ok primary-fail: current=0 candidate=-22
dump headers-ok entries-fail: current=0 candidate=-22
dump headers-fail: current=-95 candidate=-95
```

The first line is the key compatibility control: the candidate still ignores an optional resource-enrichment failure when the actual DPIPE table query succeeds.

## Candidate

Tracked candidate: `candidate.patch`.

For table show:

```diff
-mnlu_gen_socket_sndrcv(... DPIPE_TABLE_GET ...);
+err = mnlu_gen_socket_sndrcv(... DPIPE_TABLE_GET ...);
...
-return 0;
+return err;
```

For entry dump:

```diff
-mnlu_gen_socket_sndrcv(... DPIPE_ENTRIES_GET ...);
+err = mnlu_gen_socket_sndrcv(... DPIPE_ENTRIES_GET ...);
```

Cleanup remains unchanged.

## Duplicate search

Open and closed `iproute2/iproute2` issue searches for DPIPE table/dump error status and false-success behavior returned no matching report during this pass.

## Evidence boundary

Demonstrated:

- exact current source discards the primary table and entry receive statuses;
- both associated callbacks have meaningful error returns;
- the behavior is present at the 2017 DPIPE introduction;
- 2019 history explicitly distinguishes optional resource enrichment as a failure class that should be nonfatal;
- the candidate preserves that optional-resource behavior while returning primary-query failures;
- no matching upstream issue was found in the searches performed.

Not yet demonstrated:

- exact-head integration against hardware/driver supporting DPIPE;
- prevalence of primary request failure in ordinary environments;
- whether maintainers intentionally relied on the longstanding false-success status (no source comment or commit rationale establishing that was found).

## Cleanup

No kernel, namespace, device, DPIPE, or hardware state was changed. The reduced fixture is pure control flow.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. find a simulator or selftest surface that can exercise a DPIPE request failure without external hardware;
2. continue the command-wrapper audit for other places where the final/primary receive status is dropped;
3. keep the DPIPE and #613 shared-buffer findings separate because their history differs (longstanding vs regression).

External-contact state: no upstream interaction authorized or made.
