# iproute2 devlink resource output truncates u64 fields

Date: 2026-08-12

## Finding

At current iproute2 head `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`, `resource_parse()` correctly decodes `RESOURCE_OCC`, `RESOURCE_SIZE_MIN`, and `RESOURCE_SIZE_GRAN` with `mnl_attr_get_u64()` into `uint64_t` fields. `resource_show()` later renders those three through `print_uint()`, whose value type is `unsigned int`.

The same function already renders `size`, `size_new`, and `size_max` with the u64 helper, so these three fields are local width outliers.

Current Linux serializes occupancy, minimum size, maximum size, and granularity with `devlink_nl_put_u64()`. Resource internals and size parameters are u64 as well.

## History

Resource support was introduced by `8cd644095842af3107320e86eeb01be6af6c77bb`. Its `struct resource` used `uint64_t` for size/min/max/granularity/occupancy from the beginning, while output went through an unsigned-int helper.

Commit `c3f69bf923dea50e48564fd520fec6314ddbcf5f` later fixed the resource set argument specifically because “Resource size is a 64 bit attribute at netlink level,” but did not address these output fields.

## Current mismatches

```c
if (resource->occ_valid)
    print_uint(... resource->size_occ);
...
print_uint(... resource->size_min);
pr_out_u64(... resource->size_max);
print_uint(... resource->size_gran);
```

## Candidate

`candidate.patch` routes `occ`, `size_min`, and `size_gran` through `pr_out_u64()`, matching the already-correct size/max paths.

## Reduced boundary

`repro.c` demonstrates that values at or above 2^32 are changed by the current unsigned-int output boundary while the candidate preserves them.

## Duplicate search

Open and closed upstream issue searches for resource occupancy/min/granularity u64 truncation returned no match during this pass.

## Evidence boundary

Demonstrated: exact current source, Linux u64 producer contract, 2018 history, prior 2019 full-range resource-size precedent, reduced narrowing fixture.

Not demonstrated: a current device exposing occupancy/minimum/granularity above 2^32 in an integration run. The width mismatch is protocol-correctness evidence; prevalence remains separate.

No upstream contact was made.
