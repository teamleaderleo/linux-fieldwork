LIVE CHECKPOINT

Unit: fuse-overlayfs FUSE_DONT_MASK request umask handling
Worker or variant: LF-R17 / Rust-rewrite create-mode semantics
Exact head: containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117
Question: Does the Rust rewrite honor the per-request umask after negotiating FUSE_DONT_MASK?
Observed so far: no. create/mkdir/mknod all receive `_umask` and ignore it. Linux/fuser define DONT_MASK as disabling kernel-side create masking. The C implementation negotiated the same capability and explicitly applied ctx->umask. Current mknod additionally widens backing mode with unconditional `| 0755`, while C made that conditional on xattr_permissions.
Changed paths: Fieldwork only — repro.py, candidate.patch, README.md, STATUS.md
Completed gates: current init/callback source; Linux and fuser DONT_MASK contract; pre-Rust C init/create/mkdir/mknod controls; exact rewrite introduction; duplicate/test search; reduced caller-vs-daemon umask discriminator
Cleanup state: no external/kernel/device state created
Evidence boundary: exact source/history + Linux/fuser primary contracts + reduced mode model; no exact-head mounted multi-process integration
Next safe action: owned mounted multi-umask test if available; reconstruct stat-override/do_fchown semantics for xattr_permissions creation paths; audit other negotiated userspace-responsibility capabilities
External-contact state: no upstream interaction authorized or made
