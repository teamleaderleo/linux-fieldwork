LIVE CHECKPOINT

Unit: fuse-overlayfs signed pre-epoch timestamp preservation
Worker or variant: LF-R11 / Rust-rewrite semantic drift
Exact head: containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117
Question: Does the Rust rewrite preserve valid timestamps before 1970 in both stat replies and setattr requests?
Observed so far: no. Read-side `stat_to_attr()` casts negative signed seconds to u64 before `SystemTime` addition; Rust's Unix SystemTime cannot represent that huge positive duration and Add panics on checked-add failure. Setattr uses `duration_since(UNIX_EPOCH).unwrap_or_default()`, rewriting every pre-epoch specific time to epoch zero.
Changed paths: Fieldwork only — candidate.patch, repro.py, README.md, STATUS.md
Completed gates: current-source read/set paths; normal-request reachability; Rust std SystemTime representation/panic boundary; pre-Rust C behavior; exact Rust rewrite introduction; local negative-filesystem timestamp control; fuser signed-time precedent; test search; open/closed upstream issue search
Cleanup state: temporary regular file removed; no mount/namespace/device state created
Evidence boundary: exact source/history + primary Rust/fuser sources + local filesystem control; no exact-head mounted/compiled integration because rustc is unavailable locally
Next safe action: seek owned-fork/CI compile path if available, then audit adjacent Rust-rewrite signed conversions
External-contact state: no upstream interaction authorized or made
