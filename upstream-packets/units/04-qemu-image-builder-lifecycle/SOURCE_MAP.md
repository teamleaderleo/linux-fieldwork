# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | `mmdebstrap-autopkgtest-build-qemu` | upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94`; file last changed by `ff91e582194f99c72c460815d2fc32018aad9e97` | 487-line executable shell script |
| Linux Fieldwork import | `upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu` | blob `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3` | Exact blob match with reviewed public mirror |
| Public mirror check | `deepin-community/mmdebstrap:mmdebstrap-autopkgtest-build-qemu` | blob `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3` | Byte-identity evidence only; canonical destination remains Forgejo |
| Upstream static entry point | `coverage.sh` | mirror head `574048f2a720057b75e56622003932f344dc700a` | Runs shellcheck and shfmt on the builder |
| Upstream broader tests | `coverage.py`, `coverage.txt`, `tests/` | upstream `main` | No focused dynamic builder test located in this pass |
| Contribution destination | Forgejo pull requests | current canonical repository | Public action requires explicit authorization |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Classification |
| --- | --- | --- | --- |
| Issue #170 / PR #172 | head `4df670ee35eae4705fc49cfec5e1765a308dc88a` | Terminating signal cleanup mechanism | Component evidence; superseded for landing |
| Issue #191 / PR #192 | head `ece02b92001a3612731368354f495f6a7d969f84` | Private construction and atomic publication mechanism | Component evidence; superseded for landing |
| Issue #193 / PR #195 | head `b7fbc7e6dcf40e95d17b7cb67fc96c710571f154`; merge `a0ec62f64fd6a9ff2cc20b28142ec876c52a5145` | Explicit composition, path repair, final tests | Canonical source composition |
| Issue #397 unit 4 | branch `upstream/unit-04-qemu-image-builder-lifecycle`; draft PR #400 | Current-upstream packet, CI, and authorization gate | Canonical packet |

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
| packet `tests/test_packet_patch.py` | Full reduced lifecycle matrix and optional exact-source application | Direct publication and cleanup-only signal action | Publication, terminal signals, cleanup precedence, path rejection, reruns |
| repository `tests/test_unit04_qemu_packet_patch.py` | Exact imported-source packet gate | Sliced-tail coordinates require an offset | Upstream-root paths, full-file coordinates, no fuzz, no offset, `sh -n` green |
| packet `scripts/verify_lifecycle_model.py` | Independent baseline/candidate control | Parent-only TERM resumes and exits 0 | Candidate exits 143, preserves existing output, omits later work |
| same | Failure, success, late TERM | Final path exposed early or cleanup owns published result | Existing output preserved; one publication; late TERM retains bytes |
| same | Trailing slash | Destination spelling can be reinterpreted | Rejected before private state |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-04-qemu-image-builder-lifecycle`
- Internal Linux Fieldwork review: draft PR #400
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS EXACT CANDIDATE HEAD`
- Retained patch: `patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch`
- Patch SHA-256: `0ef272d4613e1744957630c5de7da081e248601f934aa98efb43ea22b143c4dd`
- Patch application command: `patch --batch --forward --fuzz=0 -p1 -i <packet>/patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch`

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| Final image pathname during build | Every image mutator | Publication rename only | Patch source assertions |
| Partial image | Caller-selected final path | `IMAGE_TMP` inside private sibling | Failure matrix |
| Work directory cleanup | Shared EXIT/signal trap | `cleanup()` called by distinct finalizers | Cleanup-call matrix |
| Signal result | Interrupted shell control flow | `signal_exit` with conventional status | HUP/INT/TERM matrix |
| Ordinary cleanup failure | Implicit shell behavior | `exit_cleanup` after successful command | Cleanup precedence matrix |
| Published image after rename | Cleanup ownership ambiguous | Final pathname; private ownership cleared | Post-publication TERM matrix |

## Overlap and current upstream state

Reviewed 2026-07-31 PDT and carried forward on 2026-08-01 +08:00. The canonical upstream repository lists `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`; the builder's listed last change is `ff91e582194f99c72c460815d2fc32018aad9e97`. The imported file and reviewed public mirror file share Git blob `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3`, and the baseline lifecycle remains present. No equivalent active upstream issue or pull request was identified in the reviewed issue list and repository search.

## Files deliberately outside this unit

- `mmdebstrap`: separate program and lifecycle.
- `run_qemu.sh`: issue #397 unit 5.
- `coverage.py`: issue #397 unit 11.
- `make_mirror.sh`: separate signal/proxy units.
- Focused Linux Fieldwork carrier files: retained unchanged as evidence.
