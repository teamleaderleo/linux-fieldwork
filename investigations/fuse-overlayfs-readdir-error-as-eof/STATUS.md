LIVE CHECKPOINT

Unit: fuse-overlayfs directory iterator error ownership
Worker or variant: LF-R12 / Rust-rewrite API semantic drift
Exact head: containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117
Question: Can a backing readdir error be mistaken for EOF and cache a partial directory as exhaustive?
Observed so far: yes by exact source/type-state analysis. DirStream maps NULL to None without errno handling; the DataSource iterator cannot carry errors; load_dir_impl marks the parent loaded after the loop; loaded cache misses disable lazy backing lookup. Pre-Rust C distinguished NULL+errno from EOF.
Changed paths: Fieldwork only — repro.py, CANDIDATE.md, README.md, STATUS.md
Completed gates: current sys wrapper; DataSource contract; direct adapter; overlay loaded-state consequence; pre-Rust C control; rewrite introduction; issue/test search; reduced state-machine discriminator
Cleanup state: no external/kernel/device state created
Evidence boundary: exact source/history + reduced state model; no mounted EIO-injection integration
Next safe action: fake DataSource/iterator integration in owned CI if available; continue audit for other Option APIs collapsing errno-bearing C results
External-contact state: no upstream interaction authorized or made
