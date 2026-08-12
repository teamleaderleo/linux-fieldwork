LIVE CHECKPOINT

Unit: devlink resource u64 output width
Worker or variant: LF-R10 / netlink width audit
Exact head: iproute2/iproute2@7385bcedf313c1e2edfc1e17c0a3659e2f137d7d
Question: Do resource occupancy/minimum/granularity values lose upper 32 bits in output?
Observed so far: yes by exact source/API inspection. They are parsed as u64 but rendered through `print_uint()`; sibling size fields use the correct u64 helper.
Changed paths: Fieldwork only — candidate.patch, repro.c, README.md, STATUS.md
Completed gates: current parse/render check; Linux u64 serializer check; 2018 introduction history; 2019 full-range-size precedent; open/closed issue search; reduced narrowing fixture
Cleanup state: no external/kernel/device state created
Evidence boundary: exact source/API/history plus reduced integer fixture; no >2^32 device integration
Next safe action: prevalence check if useful, otherwise switch to a fresh project/lane
External-contact state: no upstream interaction authorized or made
