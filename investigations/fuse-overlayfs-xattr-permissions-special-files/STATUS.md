LIVE CHECKPOINT

Unit: fuse-overlayfs special-file stat override under xattr_permissions
Worker or variant: LF-R18 / Rust-rewrite stat-override regression
Exact head: containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117
Question: Are logical modes/types for devices/FIFOs/sockets preserved when backing permissions are widened under xattr_permissions?
Observed so far: no. Current mknod unconditionally widens backing mode, does not write create-time override metadata, and production override_mode() returns early for every special file even though its parser supports/tests extended special-file types. A 2023 C fix explicitly separated backing mode from caller-masked logical mode.
Changed paths: Fieldwork only — repro.py, CANDIDATE.md, README.md, STATUS.md
Completed gates: current mknod source; override-xattr write search; production stat wrapper; extended parser/unit tests; 2023 device-mode fix; NEWS historical contract; exact Rust rewrite introduction; open/closed issue search; reduced reachability/mode model
Cleanup state: no device/mount/namespace state created
Evidence boundary: exact source/history + reduced mode model; no rootless mounted special-file integration
Next safe action: production-wrapper override test in owned CI; reconstruct do_fchown creation semantics for regular/dir; audit special-file copy-up override preservation
External-contact state: no upstream interaction authorized or made
