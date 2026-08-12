# Kernel producer prevalence check

Date: 2026-08-12

The u64 counter issue is reachable through an active kernel DPIPE producer, not merely permitted by an abstract wire type.

Current Linux Mellanox mlxsw DPIPE code (`drivers/net/ethernet/mellanox/mlxsw/spectrum_dpipe.c`) prepares ERIF entries with:

```c
u64 cnt;
...
entry->counter = 0;
entry->index = mlxsw_sp_rif_index(rif);
...
err = mlxsw_sp_rif_counter_value_get(..., &cnt);
if (!err) {
    entry->counter = cnt;
    entry->counter_valid = true;
}
```

So enabled ERIF DPIPE counters are populated from a true `u64` hardware/router counter and exported through the same `devlink_dpipe_entry.counter` field that current iproute2 later narrows via `print_uint()`.

This makes the counter half of the finding practically relevant: a cumulative traffic counter can naturally exceed `UINT32_MAX` without an unusual index allocation scheme.

The mlxsw ERIF entry index in this producer is based on a RIF index and is likely much smaller in normal deployments. That does not invalidate the index-width defect, but prevalence should be stated asymmetrically:

- counter > 2^32: realistic with sustained traffic on a supported producer;
- entry index > 2^32: API-correct and mishandled by userspace, but no current producer with such a large index was established in this pass.

No upstream interaction was made.
