# ManagedOOM report message atomicity

Updated: `2026-08-05`  
Controlled draft: `teamleaderleo/systemd#24`  
Branch: `linux-fieldwork/oomd-batch-updates`  
External contact: `false`

## Why this lane exists

The live Varlink method receives:

```text
ReportManagedOOMCGroups(cgroups: ControlGroup[])
```

One message can therefore contain multiple property/path mutations. The model registry previously exposed only one incremental update at a time.

Calling that API once per array element would create an invalid transaction boundary:

1. element A validates and publishes;
2. element B is malformed or allocation fails;
3. the method returns an error after element A has already changed live policy.

That is not message atomicity. It can also expose a temporary effective winner assembled from only part of the sender's report.

## Selected contract

The complete incoming array must first be parsed into typed update entries. Then one registry call applies the whole array:

```text
wire array
  -> typed OomdPolicySnapshotEntry[]
  -> oomd_reporter_adapter_apply_updates()
  -> oomd_reporter_registry_apply_updates()
  -> oomd_policy_store_apply_updates()
```

The name `OomdPolicySnapshotEntry` is reused for the typed key/value representation. In an incremental array:

- non-NULL `value` means add or replace that source contribution;
- NULL `value` means withdraw that source contribution;
- duplicate `(property, path)` keys in one message are rejected;
- validation or allocation failure publishes nothing;
- an empty update array is a no-op for an initialized active generation;
- pending or stale generations are rejected before policy mutation.

## Policy-store transaction

The store validates every entry before constructing candidate state:

- authority kind and UID;
- property enum;
- non-null absolute normalized path;
- value shape for the property;
- no duplicate property/path key in the array.

It then builds one candidate contribution array:

1. copy existing contributions not replaced by this authority's update keys;
2. append each non-withdrawal update;
3. publish the candidate only after all copies succeed.

The live store is untouched on any error.

## Focused matrix

Draft PR `teamleaderleo/systemd#24` adds `test-oomd-reporter-batch` covering:

- multiple valid updates commit together;
- a malformed later update rolls back an earlier valid update;
- duplicate keys are rejected without state change;
- multiple withdrawals commit together;
- an empty active-generation update array is a no-op;
- a null path is rejected without state change;
- a pending generation cannot apply an incremental array.

Its focused workflow also reruns the existing policy, lifecycle, registry, and link-adapter tests.

## Current head and gate

```text
head: 9dda25829ede2fa69c0899aa339273c520e00d59
workflow: Fieldwork OOMD batch updates
status: exact-head result pending at this checkpoint
```

No compile or behavioral pass is claimed until the exact-head artifact is inspected.

## Live parser requirements

The eventual native parser must not mutate policy while decoding the array. It should:

1. authenticate and resolve the reporter link;
2. determine first-snapshot versus incremental mode;
3. parse every JSON object into owned typed values;
4. reject an invalid object or duplicate key for the complete message;
5. call exactly one snapshot or update-array transaction;
6. free the typed message after the registry call;
7. translate effective-state changes into monitored-map updates only after the policy transaction succeeds.

This is a deliberate tightening from the current path, which skips malformed array elements and can publish other elements from the same message.

## Boundary

This lane does not parse JSON, modify `oomd-manager.c`, or define the external error response. It establishes the internal transaction that the live parser must call.

## Authority

Internal controlled-fork work only. No action has occurred in `systemd/systemd`.
