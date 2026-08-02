# LF-35 Result — Python, Rust, and ML Infrastructure Round 003

Date: 2026-08-03  
Worker or variant: `LF-R02`  
Branch: `research/lf-35-round-003-python-rust-ml`  
State: `ACTIVE — THREE FOCUSED RUNS QUEUED`  
External contact authorized: `false`

## In simple words

This round follows the controlled fork inventory and current public work instead of recycling the old package shortlist. It prioritizes Python tooling implemented in Rust, deterministic ML infrastructure, and GPU/runtime systems where local fixtures can distinguish behavior without requiring a production model deployment.

The current strongest controlled repository remains `teamleaderleo/uv`, but it already contains substantial active Fieldwork. New scouting must exclude those existing lanes before claiming a fresh target.

## Actions execution started

### Biome losing tests

Controlled repository: `teamleaderleo/biome`  
Exact upstream source base: `9847e680ff8bb891a6c910e881af98a4fffa33c2`

| Investigation | Internal draft PR | Exact CI head | Focused run | Last observed state |
| --- | --- | --- | --- | --- |
| mutable member truthiness | `teamleaderleo/biome#2` | `a10c7b47eeed104073f01c34fdbfcb437e5fd66b` | `30759307070` | queued |
| Git-internal watcher paths | `teamleaderleo/biome#3` | `05cfbc652f4557e77c5508bba9bb4894694ef98a` | `30759313961` | queued |

The existing Biome pull-request workflow uses private Depot runners. A separate controlled base, `ci/biome-focused-base`, carries one GitHub-hosted Ubuntu workflow. Each draft PR routes exactly one focused test and skips the unrelated job.

No queued run has been rerun or cancelled. No result is claimed until a runner completes the exact job.

### uv stubs-package discriminator

Controlled repository: `teamleaderleo/uv`  
Exact public source base: `79bbface771210df216b738e9bdc7df95e5a9e6b`

| Item | Exact value |
| --- | --- |
| CI base | `ci/uv-20734-base@f86ccacae9f69d4e77e91ae0e6659772cdb46707` |
| Research branch | `research/uv-20734-stubs-init-mismatch` |
| Research head | `60915b1952f4655d4c0223f4fa43b65e68a2633b` |
| Internal draft PR | `teamleaderleo/uv#23` |
| Focused run | `30759500353` |
| Last observed state | queued |

The discriminator builds uv, creates a package named `foo-stubs`, records the generated tree, and runs `uv build`. Current source has a cross-component mismatch:

- `uv init --package` uses the distribution-normalized name and creates `src/foo_stubs/__init__.py`;
- `uv-build-backend` recognizes the `-stubs` suffix and requires `src/foo-stubs/__init__.pyi`.

The run is execution-only. It selects neither the initializer nor the build backend as the final correction owner.

## Existing uv work excluded from new-target claims

The controlled uv fork already contains active or retained work for:

- extracted-wheel cache crash consistency and recovery;
- PEP 723 lockfile authority through symlinks;
- relative-path/source-provenance lockfile serialization;
- uv lockfiles passed as requirements diagnostics;
- BusyBox and Fish relocatable launcher behavior;
- Windows self-update interruption, finalization, recovery journals, and Job Object process-tree ownership.

These are real current lanes, not empty candidates. Round 003 does not rank them again.

## Current uv issue overlap screen

| Public issue | Distinguishing value | Current overlap | Disposition |
| --- | --- | --- | --- |
| `astral-sh/uv#20734` | exact generated-project/build mismatch; local fixture | no PR referencing `20734` found | selected for execution |
| `#20672` | fully local offline URL-lookahead resolver graph | PRs `#20736` and `#20738` | review/compare only |
| `#20675` | interrupted Python install leaves large `.temp` state | PRs `#20752` and `#20754` | review/compare only |
| `#20477` | relative source path becomes absolute in lockfile | PR `#20631`; controlled fork already has deeper executed lane | existing work |
| `#20744` | requirements continuation before version specifier | PRs `#20751` and `#20787` | duplicate implementation stop |
| `#20852` | trampoline Docker/nightly mismatch | PR `#20853` | duplicate implementation stop |
| `#19429` | blocking tempfile creation on async paths | PRs `#20089` and `#20513` | review/compare only |
| `#20818` | prerelease constraints regression after 0.12 behavior change | no product-fix PR identified in first overlap pass | deeper contract review |
| `#20678` | workspace `uv add --index` persists ineffective index configuration | overlap not yet resolved | deeper source map |
| `#18968` | audit ignore configuration differs between host and Debian container | exact container fixture appears feasible | reproduction candidate |

## ML infrastructure screen

### Safetensors

The repository is currently `safetensors/safetensors`.

| Public issue | Value | Overlap | Disposition |
| --- | --- | --- | --- |
| `#817` | 32-bit/wasm size validation rejects a valid ~787 MB tensor | PR `#818` | review/target-execution only |
| `#584` | randomized metadata ordering prevents byte-identical output | PR `#790` | duplicate implementation stop |
| `#812` | s390x serialization test loads corrupted floating-point values | no PR referencing `812` found | selected for source investigation |
| `#607` | serialized tensor storage may violate accelerator alignment | no overlap checked yet; model-heavy reproduction | secondary |
| `#821` / `#729` | mmap-backed host-to-device transfer stalls | hardware-specific ROCm/CUDA | performance lab, not first CI lane |

Issue `#812` is not yet proven to be a concurrency defect. Current source shows:

- the high-level NumPy save path detects non-little-endian arrays and creates a byteswapped buffer before serialization;
- the low-level public `TensorSpec` path borrows raw bytes from `data_ptr` and serializes them unchanged;
- the new GIL-release test constructs `TensorSpec` directly from native NumPy pointers;
- the `TensorSpec` safety text documents pointer lifetime, but not the required byte order.

On a big-endian host, the test bypasses the byte-swap performed by the normal NumPy API. The first question is therefore whether the low-level API promises native-endian tensors, requires little-endian buffers, or needs an explicit byte-order field. Do not attribute the observed corruption to threading until a single-thread direct-`TensorSpec` control is run.

### Tokenizers

`huggingface/tokenizers#1636` has a small `NormalizedString.clear()`/append reproducer, but PR `#1660` already proposes a fix. It is useful for review and current-head validation, not empty implementation work.

### Controlled ML-adjacent repositories

The current controlled inventory includes `teamleaderleo/wgpu`. That creates a branchable Rust/GPU systems lane for mapping, resource lifetime, backend portability, and validation issues. No major controlled fork named PyTorch, Transformers, Tokenizers, Safetensors, Candle, Burn, JAX, PyO3, Maturin, Pydantic, or Polars was found in the connected inventory queries used in this pass.

## Ranking direction

The current order for deeper work is:

1. execute and classify uv `#20734`;
2. reduce safetensors `#812` into single-thread/direct-pointer/high-level-wrapper controls;
3. inspect `uv #20818`, `uv #20678`, and `uv #18968` for exact current source and overlap;
4. scout current `wgpu` issues for small validation or mapping fixtures;
5. treat GPU model-loading performance issues as capability-dependent labs, not quick source candidates.

## Evidence boundary

No public issue, pull request, comment, review, reaction, or email was created. Internal draft PRs exist only in controlled forks. The three focused GitHub Actions runs are queued, not complete. No model weights, GPU instance, external registry credential, private package index, or production environment was used.
