# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | `mmdebstrap-autopkgtest-build-qemu` | upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94`; file last changed by `ff91e582194f99c72c460815d2fc32018aad9e97` | 487-line executable shell script |
| Linux Fieldwork import | `upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu` | blob `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3` | Exact blob match with public mirror |
| Public mirror check | `deepin-community/mmdebstrap:mmdebstrap-autopkgtest-build-qemu` | blob `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3` | Byte-identity evidence only; canonical destination remains Forgejo |
| Upstream static entry point | `coverage.sh` | mirror head `574048f2a720057b75e56622003932f344dc700a` | Runs shellcheck and shfmt on the builder |
| Upstream broader tests | `coverage.py`, `coverage.txt`, `tests/` | upstream `main` | No focused dynamic builder test located in this pass |
| Contribution destination | Forgejo pull requests | current canonical repository | Public action requires explicit authorization |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Classification |
| --- | --- | --- | --- |
| Issue #170 / PR #172 | head `4df670ee35eae4705fc49cfec5e1765a308dc88a` | Terminating signal cleanup mechanism | Component evidence; superseded for landing |
| Issue #191 / PR #192 | head `ece02b92001a3612731368354f495f6a7d969f84` | Private construction and atomic publication mechanism | Component evidence; superseded for landing |
| Issue #193 / PR #195 | head `b7fbc7e6dcf40e95d17b7cb67fc96c710571f154`; merge `a0ec62f64fd6a9ff2cc20b28142ec876c52a5145` | Explicit composition, path repair, final tests | Canonical |
| Issue #397 unit 4 | branch `upstream/unit-04-qemu-image-builder-lifecycle` | Current-upstream packet and authorization gate | Canonical packet |

## Candidate code

| File | Lines or symbols | Change | Owning patch |
| --- | --- | --- | --- |
| `mmdebstrap-autopkgtest-build-qemu` | `WORKDIR`, `prepare_image`, `publish_image`, `cleanup`, `exit_cleanup`, `signal_exit` | Private image ownership, cleanup, signal exits | patch 0001 |
| same | `mke2fs` arguments | Route initial image creation to `IMAGE_TMP` | patch 0001 |
| same | `truncate`, `sfdisk`, `dd` | Route remaining image mutations to `IMAGE_TMP` | patch 0001 |
| same | final success path | Publish once before success message | patch 0001 |

## Candidate tests

| File | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| `tests/test_packet_patch.py` | Exact imported-source patch application | Sliced-tail hunk coordinates require an offset | Full-file coordinates, no fuzz, no offset, `sh -n` green |
| same | Existing and absent final output on failure | Partial output can occupy final name | Existing bytes/mode preserved; absent path remains absent |
| same | Wrapper-only HUP/INT/TERM | Cleanup-only trap can resume | 129/130/143, later work omitted, cleanup once |
| same | Immediate rerun | Residue can block same target | Rerun publishes complete bytes |
| same | Post-publication TERM | Cleanup can own wrong path | 143 while published image remains |
| same | Cleanup failures | Cleanup can obscure primary result | 74 only after clean success; 42 and signal results remain primary |
| same | Trailing slash | Utilities reinterpret destination | Rejected before `mktemp` |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-04-qemu-image-builder-lifecycle`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS EXACT CANDIDATE HEAD`
- Retained patch: `patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch`
- Patch application command: `patch --batch --forward --fuzz=0 -p1 -i <packet>/patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch`

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| Final image pathname during build | Every image mutator | Publication rename only | Patch source assertions |
| Partial image | Caller-selected final path | `IMAGE_TMP` inside private sibling | Failure matrix |
| Work directory cleanup | Shared EXIT/signal trap | `cleanup()` called by distinct finalizers | Cleanup-call matrix |
| Signal result | Interrupted shell control flow | `signal_exit` with conventional status | HUP/INT/TERM matrix |
| Ordinary cleanup failure | Implicit shell behavior | `exit_cleanup` after successful command | Cleanup precedence matrix |
| Published image after rename | Cleanup still ambiguous | Final pathname; private ownership cleared | Post-publication TERM matrix |

## Overlap and current upstream state

Reviewed 2026-07-31 PDT. The canonical upstream repository lists `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`; the builder's listed last change is the April 2025 shfmt commit `ff91e582194f99c72c460815d2fc32018aad9e97`. The imported file and public mirror file share Git blob `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3`, and the baseline lifecycle remains present. No equivalent active upstream issue or pull request was identified in the reviewed issue list and repository search.

## Files deliberately not changed

- `mmdebstrap`: separate program and lifecycle.
- `run_qemu.sh`: owned by issue #397 unit 5.
- `coverage.py`: cancellation ownership is issue #397 unit 11.
- `make_mirror.sh`: separate signal/proxy units.
- Existing focused Linux Fieldwork carrier files: retained unchanged as evidence.
