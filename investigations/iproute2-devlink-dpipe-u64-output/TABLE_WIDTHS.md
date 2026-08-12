# DPIPE table-level u64 follow-up

Date: 2026-08-12

The same width family from #615 also affects table-level DPIPE metadata.

## Current iproute2

`dpipe_table_show()` currently declares:

```c
uint32_t resource_units;
uint32_t size;
```

and then reads/prints:

```c
size = mnl_attr_get_u32(nla_table[DEVLINK_ATTR_DPIPE_TABLE_SIZE]);
print_uint(..., size);
...
resource_units = mnl_attr_get_u32(
    nla_table[DEVLINK_ATTR_DPIPE_TABLE_RESOURCE_UNITS]);
print_uint(..., resource_units);
```

`DEVLINK_ATTR_DPIPE_TABLE_SIZE` is already listed as `MNL_TYPE_U64` in iproute2's policy.

`DEVLINK_ATTR_DPIPE_TABLE_RESOURCE_ID` and `DEVLINK_ATTR_DPIPE_TABLE_RESOURCE_UNITS` were not listed in the current policy table during this pass, despite being decoded later.

## Current Linux producer contract

`net/devlink/dpipe.c::devlink_dpipe_table_put()` obtains table size into `u64 table_size` and serializes it with `devlink_nl_put_u64()`.

The same function serializes both resource ID and resource units with `devlink_nl_put_u64()`:

```c
devlink_nl_put_u64(... DEVLINK_ATTR_DPIPE_TABLE_RESOURCE_ID,
                   table->resource_id);
devlink_nl_put_u64(... DEVLINK_ATTR_DPIPE_TABLE_RESOURCE_UNITS,
                   table->resource_units);
```

So both `size` and `resource_units` have the same 64-bit wire contract as the entry index/counter fields already tracked in #615.

## Candidate expansion

`candidate.patch` was expanded in commit `27ded3462e9d0f4b266427ed686fd9b1270870fd` to:

- validate DPIPE table resource ID/units as u64;
- decode table size and resource units with `mnl_attr_get_u64()`;
- keep them in `uint64_t`;
- render with `print_u64()`;
- retain the already tracked u64 entry index/counter changes.

This makes the candidate a coherent DPIPE wire-width repair instead of four isolated casts.

No upstream interaction was made.
