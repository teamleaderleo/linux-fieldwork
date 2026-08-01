# Source map — unit 05

## Canonical target and controlled candidate

| Item | Exact value | Role |
| --- | --- | --- |
| Project | mmdebstrap | Upstream target |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` | Final source of truth |
| Canonical branch | `master` | Final rebase and submission target |
| Controlled mirror | `https://github.com/teamleaderleo/mmdebstrap` | Candidate repository |
| Controlled base | `574048f2a720057b75e56622003932f344dc700a` | Exact mirror base |
| Base `run_qemu.sh` blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` | Exact imported-source identity |
| Base SHA-256 | `da89b51df80786f4e379b2ba5b033aab6c4e1d7acc8ba17cf57e67159a32e300` | Byte receipt |
| Base size | 2,029 bytes | Byte receipt |
| Candidate branch | `linux-fieldwork/unit-05-run-qemu-result-precedence` | Five-commit candidate |
| Candidate head | `6efe6945f9f89cff57fe84086ede7bda747c3879` | Exact candidate head |
| Candidate file blob | `1fc816d6fe982351f6519fd1458329112eebdcfb` | Exact candidate source |
| Candidate SHA-256 | `434e7b6b9c32e30b506ea6af121608414c42b668c329e6395e75e19dc09ff276` | Byte receipt |
| Candidate size | 3,095 bytes | Byte receipt |

Compare against controlled `master`:

```text
status: ahead
ahead: 5
behind: 0
base and merge base: 574048f2a720057b75e56622003932f344dc700a
changed files: 1
run_qemu.sh: 64 additions, 10 deletions
```

## Candidate commit series

| Order | Commit | Purpose |
| ---: | --- | --- |
| 1 | `614fb26a4f0724618a5eecd3ce1bee12454ff7de` | Separate ordinary and signal cleanup; preserve host, guest, and first cleanup failure |
| 2 | `cb6ef6d6c2b1368b3603b2ec06635c3815f31e11` | Keep later handled signals from replacing the first or interrupting cleanup |
| 3 | `13cf34fd87d44b4d37c6767fdbd153b2ef535a57` | Retain the first signal during ordinary EXIT cleanup |
| 4 | `457095c6f89655ab12b7055307f519e71bb0dbca` | Preserve completed guest failure before a later cleanup signal |
| 5 | `6efe6945f9f89cff57fe84086ede7bda747c3879` | Close signal-handler entry windows before overlapping signals can re-enter |

## Canonical Linux Fieldwork lineage

| Carrier | Exact identity | Role |
| --- | --- | --- |
| Issue #269 | completed | Original result-overwrite and cleanup lifecycle owner |
| Issue #297 | completed | Completed-guest-before-cleanup-signal policy |
| PR #270 | head `76ffad2ea25f03272c788d37de6232b6a0b287d7` | Patches 1–2 and predecessor controls |
| PR #282 | head `e973546c350682e1175fa68fbf705c83487c2cf9` | Patch 3 and ordinary-cleanup signal mechanism |
| PR #290 | head `3843065077c233f9f8f8b3466873cad511c8d36f` | Fixture-repair history only |
| PR #304 | head `0d5864c53badee91b403676ecc55e7aef5c38679` | Patch 4 and losing policy comparison |
| PR #319 | head `2fe3f99364df29de217536dc35a4d03b10f49640`; merge `b196d6b45f496d8eb2d763922532ad257f24bba8` | Historical four-patch composition |
| PR #319 CI | run `30628645668`, job 889 | 276 passing repository tests |
| Complete-diff repair | controlled head `6efe6945f9f89cff57fe84086ede7bda747c3879` | New patch 5 after setup-window review |

## Retained packet patches

| Order | Packet path | Git blob | Purpose |
| ---: | --- | --- | --- |
| 1 | `patches/0001-preserve-primary-result.patch` | `387b0e1d9ae0adb067a2efdc5177bf8e6814668d` | Primary result and once-only cleanup |
| 2 | `patches/0002-retain-first-signal-through-cleanup.patch` | `8f4713ab827eaf643a97ba0f9d0e9b190ab7cd49` | Explicit-signal first writer |
| 3 | `patches/0003-retain-signal-during-exit-cleanup.patch` | `227b2600851828d20861d191c1bdb54c0008ca10` | Ordinary-cleanup signal recorder |
| 4 | `patches/0004-preserve-completed-guest-before-cleanup-signal.patch` | `3769c89a002511c09350a6a9735910eb53947d66` | Guest before later cleanup signal |
| 5 | `patches/0005-close-signal-handler-setup-windows.patch` | `f7e906d915c34db6e7546e4a9b1e4024e19d98d1` | Handler-entry transition repair |

## Focused test ownership

| Test module or receipt | Primary evidence |
| --- | --- |
| `tests/test_run_qemu_result_precedence.py` | host, guest, explicit signal, success, syntax, application |
| `tests/test_run_qemu_cleanup_failure_precedence.py` | first cleanup failure while later cleanup continues |
| `tests/test_run_qemu_first_signal_cleanup.py` | competing explicit signals and cleanup completion |
| `tests/test_run_qemu_exit_cleanup_signal.py` | signals during ordinary EXIT cleanup and rerun |
| `tests/test_run_qemu_guest_before_cleanup_signal.py` | completed guest before later cleanup signal |
| `tests/test_run_qemu_handler_setup_windows.py` | explicit and EXIT handler-entry windows; Git blob `a58eb89029729a89208c72e30164bcfe3c0aa139` |
| `artifacts/2026-08-01-controlled-fork-lifecycle-matrix.txt` | 58/58 controlled-fork checks |
| `artifacts/2026-08-01-handler-setup-window-repair.txt` | losing controls and repaired widened windows |

## Project-native test path

mmdebstrap documents `./make_mirror.sh` followed by `CMD=./mmdebstrap ./coverage.sh`, with individual cases through `coverage.py`. In `coverage.py`, QEMU-classified cases execute `./run_qemu.sh`. These are the authoritative upstream-native gates after canonical rebase and mirror/cache preparation.

## Remaining source facts

Before authorization:

1. current full canonical Salsa `master` SHA and `run_qemu.sh` blob;
2. active equivalent issue, branch, or merge-request search;
3. clean rebase or identity proof onto that canonical head;
4. exact upstream-native QEMU test run identity and results;
5. exact hosted or checkout execution of the new setup-window regression module.

The controlled mirror exists and needs no user-side setup.
