LIVE CHECKPOINT

Unit: devlink shared-buffer port-pool show exit status
Worker or variant: LF-R07 / source+history error ownership
Exact head: iproute2/iproute2@7385bcedf313c1e2edfc1e17c0a3659e2f137d7d
Question: Can `devlink sb port pool show` hide a receive/kernel error and exit successfully?
Observed so far: yes by exact source inspection. Current code assigns the receive result to `err` then returns 0; the 2016 introduction returned the receive result directly, and current sibling show commands still return `err`.
Changed paths: Fieldwork only — README.md, repro.c, candidate.patch
Completed gates: current source check; sibling comparison; 2016 correct baseline; 2023 selector preimage check; open/closed upstream issue search; reduced return-value discriminator
Cleanup state: no external or kernel state created
Evidence boundary: exact source/history plus reduced return-value fixture; no exact-head hardware integration run
Next safe action: pin first bad intermediate commit if feasible, then audit sibling wrappers for other swallowed receive results
External-contact state: no upstream interaction authorized or made
