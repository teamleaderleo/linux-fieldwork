# iproute2 devlink DPIPE truncates u64 entry indexes and counters

Date: 2026-08-12

Related programme lane: LF-29 — netlink value integrity.

## TL;DR

At current iproute2 head `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`, DPIPE entry output truncates two protocol values that are defined as 64-bit:

- `DEVLINK_ATTR_DPIPE_ENTRY_INDEX` is validated as `MNL_TYPE_U64`, but `dpipe_entry_show()` stores it in `uint32_t` using `mnl_attr_get_u32()` and prints it with `print_uint()`.
- `DEVLINK_ATTR_DPIPE_ENTRY_COUNTER` is correctly read with `mnl_attr_get_u64()` into `uint64_t`, but is then passed to `print_uint()`, whose public interface accepts `unsigned int`.

Values above `UINT32_MAX` therefore lose their upper bits in user-visible output. For the entry index, the wrong-width getter also means the wire value is decoded through a 32-bit accessor before printing.

The kernel API defines both `struct devlink_dpipe_entry.index` and `.counter` as `u64`, and iproute2's own attribute policy declares both netlink attributes `MNL_TYPE_U64`.

No upstream contact is authorized or has been made.

## Exact source boundary

Project: `iproute2/iproute2`

Reviewed head: `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`

Current policy:

```c
[DEVLINK_ATTR_DPIPE_ENTRY_INDEX] = MNL_TYPE_U64,
...
[DEVLINK_ATTR_DPIPE_ENTRY_COUNTER] = MNL_TYPE_U64,
```

Current rendering:

```c
uint32_t entry_index;
uint64_t counter;
...
entry_index = mnl_attr_get_u32(nla_entry[DEVLINK_ATTR_DPIPE_ENTRY_INDEX]);
print_uint(PRINT_ANY, "index", "index %u", entry_index);

if (nla_entry[DEVLINK_ATTR_DPIPE_ENTRY_COUNTER]) {
    counter = mnl_attr_get_u64(nla_entry[DEVLINK_ATTR_DPIPE_ENTRY_COUNTER]);
    print_uint(PRINT_ANY, "counter", " counter %u", counter);
}
```

`include/json_print.h` defines `print_uint()` over `unsigned int`, while `print_u64()` accepts `uint64_t`.

## Kernel/API contract

Current Linux `struct devlink_dpipe_entry` declares:

```c
u64 index;
...
u64 counter;
```

The userspace width is therefore not an inference from naming; it is an explicit public API contract.

## History boundary

DPIPE was introduced in iproute2 by:

- `153c1a9b21e5b7b78e066de2b93a4edb8c3dc498` — `devlink: Add support for pipeline debug (dpipe)`

The introduction already declared `uint32_t entry_index`, called `mnl_attr_get_u32()` for the entry-index attribute, and fed the u64 counter to the then-32-bit unsigned output helper. This is therefore a longstanding width bug rather than a recent regression.

## Reduced discriminator

Tracked fixture: `repro.c`.

Representative 64->32 behavior:

```text
wire=0 current_uint=0 candidate_u64=0
wire=4294967295 current_uint=4294967295 candidate_u64=4294967295
wire=4294967296 current_uint=0 candidate_u64=4294967296
wire=1099511627783 current_uint=7 candidate_u64=1099511627783
wire=18446744073709551615 current_uint=4294967295 candidate_u64=18446744073709551615
```

The fixture isolates the final narrowing boundary. The entry-index path is even stricter in real source because it uses the wrong-width netlink getter before the print layer.

## Candidate

Tracked patch: `candidate.patch`.

- change `entry_index` to `uint64_t`;
- use `mnl_attr_get_u64()` for `DEVLINK_ATTR_DPIPE_ENTRY_INDEX`;
- use `print_u64(..., "%" PRIu64, ...)` for both index and counter.

No wire format or kernel behavior changes.

## Duplicate search

Open and closed upstream issue searches for combinations of `dpipe`, `entry index`, `counter`, `u64`, and `truncate` returned no matching report during this pass.

## Evidence boundary

Demonstrated:

- current iproute2 policy says both attributes are u64;
- current code decodes entry index as u32 and renders both fields through an unsigned-int output path;
- `print_uint()` accepts `unsigned int`, while `print_u64()` accepts `uint64_t`;
- current Linux devlink API defines entry index and counter as u64;
- the same width mismatch is present in the 2017 DPIPE introduction;
- a two-field local candidate preserves the full values.

Not yet demonstrated:

- an exact-head DPIPE hardware integration run with index/counter above 2^32-1;
- how common hardware/driver implementations are that produce such large values;
- output behavior on every architecture/endianness for the wrong-width `mnl_attr_get_u32()` access. The width contract itself is architecture-independent.

## Cleanup

No device, namespace, kernel, or hardware state was changed. The reduced fixture is pure integer conversion/output.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. inspect kernel DPIPE producers/drivers for realistic entry indexes or counters that can exceed 32 bits;
2. look for netdevsim or mlxsw selftests that could exercise a large counter/index;
3. continue the wider netlink-width audit in current devlink code.

External-contact state: no upstream interaction authorized or made.
