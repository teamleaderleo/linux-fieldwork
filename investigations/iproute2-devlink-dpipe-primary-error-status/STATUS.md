LIVE CHECKPOINT

Unit: devlink DPIPE primary request error ownership
Worker or variant: LF-R08 / source+history control-flow audit
Exact head: iproute2/iproute2@7385bcedf313c1e2edfc1e17c0a3659e2f137d7d
Question: Can the primary DPIPE table/entry receive fail while the command returns success?
Observed so far: yes by exact source inspection. `cmd_dpipe_table_show()` discards DPIPE_TABLE_GET status and returns 0; `cmd_dpipe_table_dump()` discards DPIPE_ENTRIES_GET status and returns the earlier header-query result. This behavior is present at the 2017 DPIPE introduction.
Changed paths: Fieldwork only — candidate.patch, repro.c, README.md, STATUS.md
Completed gates: exact current source check; callback error-path check; 2017 introduction history; 2019 optional-resource nonfatal rationale; open/closed upstream issue search; reduced compatibility/status discriminator
Cleanup state: no external/kernel/device state created
Evidence boundary: exact source/history plus reduced control-flow fixture; no exact-head DPIPE hardware integration
Next safe action: seek a simulator/selftest surface for DPIPE failure injection, then continue primary-receive error-ownership audit elsewhere
External-contact state: no upstream interaction authorized or made
