LIVE CHECKPOINT

Unit: fuse-overlayfs command-line Linux path byte preservation
Worker or variant: LF-R15 / Rust-rewrite path encoding drift
Exact head: containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117
Question: Can non-UTF8 Linux lower/upper/work/mount paths reach config parsing without panic or byte loss?
Observed so far: no. main uses std::env::args()->String, which Rust std implements with into_string().unwrap() and documents as panicking on non-Unicode argv. Config path fields are String-only. Local Linux filesystem accepts raw 0xff path components.
Changed paths: Fieldwork only — repro.py, CANDIDATE.md, README.md, STATUS.md
Completed gates: current main/config source; Rust std args panic source; rewrite introduction; pre-Rust C representation; local raw-path control; realpath lossy-conversion adjacency; upstream issue search
Cleanup state: temporary raw-byte directory removed; no mount/namespace/device state created
Evidence boundary: exact source/history + Rust std source + local filesystem control; no exact-head spawned binary because local Rust build is unavailable
Next safe action: owned CI raw-argv integration if available; continue lossy path-helper audit
External-contact state: no upstream interaction authorized or made
