LIVE CHECKPOINT

Unit: persisted stat-override mode across layer reuse
Worker or variant: LF-R20 / layer metadata durability
Exact head: containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117
Question: Does an upper layer remain self-describing when later reused as a lower layer?
Observed so far: no. Explicit xattr_permissions only changes the current upper DataSource enum; lower DataSources later detect override mode from root xattrs. Old C initialized a root override marker when missing and failed startup if it could not. Without that marker, child override xattrs can exist while later lower detection returns None.
Changed paths: Fieldwork only — repro.py, CANDIDATE.md, README.md, STATUS.md
Completed gates: current upper init; current DirectAccess root probing; in-memory setter; pre-Rust root-marker initialization; local root/child xattr reuse model; upstream duplicate search
Cleanup state: temporary directory/xattrs only; no mount/namespace/device state created
Evidence boundary: exact source/history + local xattr model; no two-mounted-session integration
Next safe action: reconstruct legacy-vs-containers marker conflict rules; owned two-lifecycle integration if available; audit other C-persisted layer metadata
External-contact state: no upstream interaction authorized or made
