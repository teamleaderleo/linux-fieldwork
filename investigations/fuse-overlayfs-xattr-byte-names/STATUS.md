LIVE CHECKPOINT

Unit: fuse-overlayfs Linux xattr byte-name preservation
Worker or variant: LF-R13 / Rust-rewrite encoding drift
Exact head: containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117
Question: Does the Rust rewrite incorrectly require xattr names to be UTF-8?
Observed so far: yes. Direct set/get/remove reject non-UTF8 OsStr names; list and copy-up silently omit them; DataSource/syscall xattr APIs use &str. Linux syscall import does not validate UTF-8, and a local regular file round-tripped user.\xff successfully.
Changed paths: Fieldwork only — repro.py, CANDIDATE.md, README.md, STATUS.md
Completed gates: current FUSE handlers; list filtering; copy-up filtering; syscall/DataSource representation; Linux fs/xattr.c ABI check; local byte-name round-trip; pre-Rust C control; rewrite introduction; upstream issue search
Cleanup state: temporary file/xattr removed; no mount/namespace/device state created
Evidence boundary: exact source/history + Linux source + local filesystem control; no exact-head mounted integration
Next safe action: owned CI/fork integration if available; audit symlink/special-file copy-up metadata preservation
External-contact state: no upstream interaction authorized or made
