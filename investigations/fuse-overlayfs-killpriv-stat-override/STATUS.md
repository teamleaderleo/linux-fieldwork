LIVE CHECKPOINT

Unit: FUSE killpriv responsibility with logical stat overrides
Worker or variant: LF-R21 / negotiated capability ownership
Exact head: containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117
Question: After advertising FUSE_HANDLE_KILLPRIV, does the logical override metadata path clear privilege state on write/chown/truncate?
Observed so far: no coherent implementation was found. Logical chown preserves cur_mode when uid/gid changes; override xattrs survive backing writes and can reassert setid mode. Old C did not advertise KILLPRIV. Conservative candidate removes the capability until a full logical/physical implementation exists.
Changed paths: Fieldwork only — repro.py, candidate.patch, README.md, STATUS.md
Completed gates: current init flag; Linux UAPI contract; current stat-override setattr path; local override-xattr write persistence; pre-Rust capability search; exact rewrite introduction; upstream duplicate search
Cleanup state: temporary regular file/user xattr only; no mount/namespace/device state created
Evidence boundary: exact source/history + Linux contract + local metadata-channel control; no exact-head mounted killpriv integration
Next safe action: owned mounted setid/write/chown/truncate test if available; audit capability-xattr clearing before re-enabling HANDLE_KILLPRIV
External-contact state: no upstream interaction authorized or made
