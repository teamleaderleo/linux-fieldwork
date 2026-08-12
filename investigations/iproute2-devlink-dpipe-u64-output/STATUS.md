LIVE CHECKPOINT

Unit: devlink DPIPE u64 entry identity/counter rendering
Worker or variant: LF-R09 / wire-width and output audit
Exact head: iproute2/iproute2@7385bcedf313c1e2edfc1e17c0a3659e2f137d7d
Question: Are u64 DPIPE entry indexes/counters truncated by userspace output?
Observed so far: yes by exact source/API inspection. Entry index is decoded with a u32 getter into uint32_t despite a u64 policy; counter is read as u64 but passed to `print_uint()`, whose value type is unsigned int.
Changed paths: Fieldwork only — candidate.patch, repro.c, README.md, STATUS.md
Completed gates: current policy check; current renderer check; json-print type check; Linux API width check; 2017 introduction history; open/closed upstream issue search; reduced narrowing discriminator
Cleanup state: no external/kernel/device state created
Evidence boundary: exact source/API/history plus reduced integer fixture; no >2^32 hardware integration
Next safe action: inspect kernel DPIPE producers for realistic large index/counter values, then continue wider netlink-width audit
External-contact state: no upstream interaction authorized or made
