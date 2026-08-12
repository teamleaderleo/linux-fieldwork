LIVE CHECKPOINT

Unit: fuse-overlayfs default ACL inheritance error ownership
Worker or variant: LF-R16 / Rust-rewrite access-control metadata
Exact head: containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117
Question: Can child creation succeed after a parent default ACL exists but target ACL application fails?
Observed so far: yes. Current inherit_acl() suppresses all parent-read errors and the final fsetxattr() result, then callers continue creation/publication. A local ext4 parent accepted/read a default ACL while a tmpfs target returned ENOTSUP applying the same ACL. The pre-Rust C helper propagated target errors and dynamically retried ACL reads on ERANGE.
Changed paths: Fieldwork only — repro.py, CANDIDATE.md, README.md, STATUS.md
Completed gates: current helper and callers; pre-Rust C helper/callers; dynamic safe_read_xattr ERANGE growth; local ext4->tmpfs ACL apply failure; exact Rust rewrite introduction; open/closed upstream issue search
Cleanup state: temporary ext4 directory/default ACL and tmpfs file removed; no mount/namespace/device state created
Evidence boundary: exact source/history + local cross-filesystem xattr control; no exact-head mounted integration or compile-tested Rust API change
Next safe action: owned/fake-xattr fault test if available; audit ACL mode/umask reconciliation and adjacent creation metadata semantics
External-contact state: no upstream interaction authorized or made
