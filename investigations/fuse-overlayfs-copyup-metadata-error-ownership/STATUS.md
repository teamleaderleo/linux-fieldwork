LIVE CHECKPOINT

Unit: fuse-overlayfs copy-up metadata error ownership
Worker or variant: LF-R14 / Rust-rewrite publication boundary
Exact head: containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117
Question: Can copy-up publish an upper object after required metadata preservation fails?
Observed so far: yes by exact source/history. Current regular and directory paths discard futimens/copy_xattr errors before rename; regular files also discard final fchmod after creating with mode|0200. Pre-Rust C aborted required metadata preservation failures.
Changed paths: Fieldwork only — repro.py, CANDIDATE.md, README.md, STATUS.md
Completed gates: current regular/directory source; helper error policy; pre-Rust C ownership/timestamp/xattr controls; exact rewrite introduction; issue search; reduced publication-state discriminator
Cleanup state: no external/kernel/device state created
Evidence boundary: exact source/history + reduced state model; no mounted syscall-failure injection
Next safe action: owned fault-injection CI if available; reconstruct rootless ownership/stat-override semantics separately; audit short-read/temp cleanup paths
External-contact state: no upstream interaction authorized or made
