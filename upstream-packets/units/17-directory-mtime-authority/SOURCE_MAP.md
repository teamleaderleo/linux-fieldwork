# Source map

## Upstream source identity

| Item | Path | Exact identity | Notes |
| --- | --- | --- | --- |
| Primary implementation | `upstream/mmdebstrap/mmdebstrap` | unit base `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`; blob `41aa46f989a2660cebdb0138e0847cde25b269a3`; version 1.5.7 | owns setup and final archive creation |
| Final tar path | same file, lines 7240–7425 on the unit base | same | sorted PAX tar, mtime clamp, one-filesystem, xattrs, pathname root traversal |
| Regression | `upstream/mmdebstrap/tests/chrootless` | imported unit base | byte-compares four root/chrootless tar pairs |
| Reproducibility contract | `upstream/mmdebstrap/README.md` | blob `281e551bdf4af6e8336dca8a93cdf278a6be4cab` | documents bit-for-bit output with `SOURCE_DATE_EPOCH` |
| Current upstream base | upstream project | `NEEDS CURRENT UPSTREAM PIN` | refresh after authority selection |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Disposition |
| --- | --- | --- | --- |
| Issue #380 | run-999 policy owner | 123 directory-only mtime differences | canonical issue |
| PR #383 | head `169d1d95d58ae362d13aec1f115fb2c0c6c58f16`; merge `2c3aa47067319163ac84512d01454fcfac08da50` | four-policy evidence matrix | canonical evidence |
| PR #384 | `5e9d64bb0bf19c1476915c23d2f6989a4bf15093` | first pathname candidate | rejected replacement race |
| PR #386 | `c8455f41347b2d113fb111726a9dd29df9f16f1e`; merge `169d1d95d58ae362d13aec1f115fb2c0c6c58f16` | symlink and real-directory identity | component evidence |
| PR #388 | `4cfc86f3549192c7207b7b3b91de1c7ab319f023` | same-device pruning | component evidence |
| PR #390 | `efb8ac9ce36b866fc7a5821cf8c5596de7501ba2` | xattr and sparse-source controls | component evidence |
| PR #391 | live `28e0e8d836a8bfc47b778b23a73b3316881be65a`; earlier executed generation `679f8b1ecae13c05013f82dc5750a424f816bd27` | real mount, ACL, capability, cleanup, rerun | component evidence |
| PR #389 | `0319755b71ec594f2019cf40cd3cf9ee68ad7d60`; merge `1d1e5c68fd6defa530ee88e0c734ac3eeb1ade2f` | descriptor-retained candidate | mechanically green; policy hold |
| Issue #392 | authority owner | inode identity versus current tree membership | canonical hold issue |
| PR #394 | `cffc0ce00f57050539a0e11f11e609d13e9ca604`; merge `0ccc162df2fcf4a9a63332eea40bebe88de0f9f3` | authority matrix | canonical authority evidence |
| PR #393 | `592eeed2bfdc4ce3e73b4693721a197eac491521` | older pathname candidate | retired history |
| PR #395 | live `74c996394819c3a717d55193d84336c2e06b3b7c`; body names earlier `e700839034a3b1ce3f3ddbfed5cf6d43a4c6987c` | current pathname carrier | held; prose identity stale |

## Packet code and tests

| File | Role | Evidence boundary |
| --- | --- | --- |
| `scripts/archive_boundary_process_probe.py` | captures ancestry, process group/session, cgroup, zombie state, root references, namespaces, and atomic JSON | Linux `/proc`; evidence only |
| `scripts/test_archive_boundary_process_probe.py` | parser, live descendant, zombie, and CLI/self-exclusion controls | local synthetic process tree |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-17-directory-mtime-authority`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Current internal candidate carriers: PR #389 and PR #395
- Packet product patch: absent pending authority selection

## Operation ownership map

| Operation | Current owner | Candidate owner | Evidence |
| --- | --- | --- | --- |
| setup and package work | mmdebstrap worker and helpers | unchanged | source and issue #392 |
| hook completion | worker socket protocol | unchanged | current source |
| directory mtime convergence | GNU tar clamp | unresolved pre-tar normalizer or archive writer | PR #383/#389/#394/#395 |
| final archive traversal | GNU tar using pathname root | unchanged in current candidates | current source |
| boundary observation | absent | packet process probe | packet scripts |
| authority policy | implicit stable completed tree | explicit after runtime receipts | issue #392 |

## Overlap and current upstream state

Internal overlap was refreshed on 2026-08-01 across the listed carriers. Public upstream overlap and the current intended base remain unrefreshed. No external contact occurred.

## Files deliberately left unchanged

- imported mmdebstrap source;
- the byte-identity chrootless regression;
- PR #389 and PR #395 candidate branches;
- the packet index, whose unit-17 entry already names this directory and `HOLD` state.
