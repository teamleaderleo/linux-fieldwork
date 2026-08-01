# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Debian baseline | `util-linux 2.41-5 amd64` |
| Installed binary | `/usr/bin/lscpu`, SHA-256 `e3c6e0c09d617cb9e77a3655f79a7a83d2dd865e49eabeccfbaa0335c9ff722e` |
| Source base | exact Debian `2.41-5` checksums in `README.md` |
| Candidate source | canonical patch `4581ede...`, effective path SHA-256 `d0460b4f...` |
| Candidate package | SHA-256 `92f3aa6f...` |
| Candidate binary | SHA-256 `88391224...` |
| Local platform | Debian GNU/Linux 13, amd64, kernel 6.12.13 |
| Privilege | unprivileged fixture execution; package build in disposable trixie container |
| Linux Fieldwork source/build head | `fefa76c37d110f8fad8a575abc1eaa9e4ed76bb1` |
| Current packet head before this update | `8ba7537bda1f7fd15a659dfb918bbc8df110419d` |

## Retained model and patch matrix

Command:

```text
/usr/bin/python3 -m unittest -v tests/test_util_linux_lscpu_cpuset_double_free.py
```

Result:

```text
Ran 5 tests in 0.082s
OK
baseline: duplicate cleanup detected (status 42)
candidate: output cleared, later cleanup is harmless (status 0)
patch dry-run/application: status 0 with --fuzz=0
fixture drift control: pass
```

Receipt: `artifacts/2026-08-01-focused-regression.txt`.

## Installed trixie package matrix

Reusable command:

```text
bash scripts/reproduce-trixie-lscpu-cpuset.sh \
  --baseline /usr/bin/lscpu \
  --output-dir OUTPUT
```

Minimal fixture result:

| Case | Status | Output identity |
| --- | ---: | --- |
| valid text | 0 | stdout SHA-256 `35adecec4503be6121100b32b103cd1239dc36bafb0a9dddb33632f552fe300d` |
| valid JSON | 0 | stdout SHA-256 `bcbc4706b6ba14380893f44f562156290c95d2f05b04bc77982330f1f374501e`; JSON parser passed |
| malformed text | 134 | stderr `free(): double free detected in tcache 2`; SHA-256 `07b68cc9fbb3f4c23a151524e4cb2429dd42b71a91cb6b7552a01230f203bc9d` |
| malformed JSON | 134 | same allocator diagnostic and digest |

The four-case results file SHA-256 is `f842fa0f827a5ce72b96dd2d219177776ac6382e038dae122baf832ca132de00`. Two fresh runs were byte-identical.

A debug malformed run exited 134; stderr was 24,142 bytes, SHA-256 `87f0166196ac9755ab24f05c3258765aa46085b105e855a8463ef498a3876d6d`. The final trace reached ordinary CPU/type cleanup before the allocator detected the duplicate free.

Receipt: `artifacts/2026-08-01-trixie-minimal-sysroot-reproduction.txt`.

## Losing control

The same malformed logical input with a larger allocation identity can exit 0. An exploratory `kernel_max` sweep produced aborting and clean values non-monotonically. The regression fixes `kernel_max=15` and uses larger values only as detector-losing controls.

## Exact source, patch, and package build

Workflow run `30690487287`, job `91344214299`, artifact `8815555088`:

- exact source checksums verified;
- effective Debian source retained the stale output;
- zero-fuzz patch dry-run passed;
- zero-fuzz real application passed;
- candidate source order verified;
- `dpkg-buildpackage -b -uc -us -j2` completed;
- candidate `.deb` and `lscpu` hashes recorded.

First red owner: fixture copier. Broad `cp -a /sys/devices/system/cpu/*` encountered unreadable container power attributes before any binary case ran. Commit `187ab0c3c72eb4f733e5c9eebaeb7b748f687fbb` replaced it with the deterministic minimal sysroot.

Receipt: `artifacts/2026-08-01-ci-run-30690487287.txt`.

## Current candidate execution runs

| Run | Head | State at handoff | Purpose |
| --- | --- | --- | --- |
| `30690810870` | `187ab0c3c72eb4f733e5c9eebaeb7b748f687fbb` | queued | first deterministic-fixture package matrix |
| `30690831292` | `8ba7537bda1f7fd15a659dfb918bbc8df110419d` | queued | exact packet-head package matrix |

Required candidate result:

- valid text and JSON status 0;
- malformed text and JSON status 0;
- JSON remains parseable;
- valid output compatibility recorded;
- no fixture, process, package, or temporary-state residue.

## Cleanup

Local fixture trees lived under `/tmp`, core files were disabled, and every tree was removed. No host sysfs write, mount, package change, socket, lock, or surviving process remained. The matrix passed the immediate clean rerun.

The Actions build used a disposable Debian trixie container. The failed run uploaded its receipts after the container exited.

## Tests still required

- candidate actual-binary matrix;
- exact valid baseline/candidate output comparison;
- util-linux native `lscpu` tests on the patched package tree;
- source-package build and debdiff for a stable-update version;
- architecture matrix;
- actual issue #4401 archive;
- ASan/Valgrind actual-package execution;
- Debian stable-update review.

## Final evidence statement

The installed trixie package defect and effective source owner are reproduced. The canonical patch applies cleanly and builds a binary package. Candidate execution remains the first incomplete gate.
