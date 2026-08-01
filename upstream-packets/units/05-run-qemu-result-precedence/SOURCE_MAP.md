# Source map — unit 05

## Canonical target and controlled mirror

| Item | Exact value | Role |
| --- | --- | --- |
| Project | mmdebstrap | Upstream target |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` | Final source of truth |
| Canonical branch | `master` | Final rebase/submission target |
| Controlled mirror | `https://github.com/teamleaderleo/mmdebstrap` | Current candidate repository |
| Mirror branch | `master` | Controlled base |
| Mirror base commit | `574048f2a720057b75e56622003932f344dc700a` | Exact candidate base |
| Target file | `run_qemu.sh` | Product source |
| Mirror base file blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` | Exact source identity |
| Mirror base SHA-256 | `da89b51df80786f4e379b2ba5b033aab6c4e1d7acc8ba17cf57e67159a32e300` | Byte receipt |
| Mirror base size | 2,029 bytes | Byte receipt |
| Candidate branch | `linux-fieldwork/unit-05-run-qemu-result-precedence` | Four-commit source candidate |
| Candidate head | `457095c6f89655ab12b7055307f519e71bb0dbca` | Exact candidate head |
| Candidate file blob | `3e8d4dc07f91d246a372749eb49ff9489c21c7b7` | Exact final source identity |
| Candidate SHA-256 | `8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f` | Byte receipt |
| Candidate size | 2,924 bytes | Byte receipt |

The mirror base file blob is exactly the imported Linux Fieldwork source blob. This closes the previous controlled-fork and live-byte-comparison gap for the mirror.

## Candidate commit series

| Order | Commit | Purpose |
| ---: | --- | --- |
| 1 | `614fb26a4f0724618a5eecd3ce1bee12454ff7de` | Separate ordinary and signal cleanup; preserve host, guest, and first cleanup failure |
| 2 | `cb6ef6d6c2b1368b3603b2ec06635c3815f31e11` | Prevent later handled signals from replacing the first or interrupting cleanup |
| 3 | `13cf34fd87d44b4d37c6767fdbd153b2ef535a57` | Retain the first signal received during ordinary EXIT cleanup |
| 4 | `457095c6f89655ab12b7055307f519e71bb0dbca` | Preserve completed guest failure before a later cleanup-time signal |

Compare result against mirror `master`:

```text
status: ahead
base and merge base: 574048f2a720057b75e56622003932f344dc700a
ahead: 4
behind: 0
changed files: 1
run_qemu.sh: 61 additions, 10 deletions
```

## Canonical Linux Fieldwork lineage

| Carrier | Exact identity | Role and disposition |
| --- | --- | --- |
| Issue #269 | completed | Original result-overwrite and cleanup lifecycle owner |
| Issue #297 | completed | Selected completed-guest-before-cleanup-signal policy |
| PR #270 | `76ffad2ea25f03272c788d37de6232b6a0b287d7`; CI 828 | Patches 1–2 and predecessor evidence |
| PR #282 | `e973546c350682e1175fa68fbf705c83487c2cf9`; CI 844 | Patch 3 and ordinary-cleanup signal mechanism |
| PR #290 | `3843065077c233f9f8f8b3466873cad511c8d36f`; CI 838 | Fixture-generation repair history; superseded as product carrier |
| PR #304 | `0d5864c53badee91b403676ecc55e7aef5c38679`; CI 854 | Patch 4 and losing-policy comparison |
| PR #319 | head `2fe3f99364df29de217536dc35a4d03b10f49640`; merge `b196d6b45f496d8eb2d763922532ad257f24bba8` | Canonical four-patch composition |
| PR #319 CI | run `30628645668`, job 889 | 276 passing repository tests |

## Retained packet patches

| Order | Packet path | Git blob |
| ---: | --- | --- |
| 1 | `patches/0001-preserve-primary-result.patch` | `387b0e1d9ae0adb067a2efdc5177bf8e6814668d` |
| 2 | `patches/0002-retain-first-signal-through-cleanup.patch` | `8f4713ab827eaf643a97ba0f9d0e9b190ab7cd49` |
| 3 | `patches/0003-retain-signal-during-exit-cleanup.patch` | `227b2600851828d20861d191c1bdb54c0008ca10` |
| 4 | `patches/0004-preserve-completed-guest-before-cleanup-signal.patch` | `3769c89a002511c09350a6a9735910eb53947d66` |

The GitHub mirror commits implement these same four changes at repository-root `run_qemu.sh`.

## Focused test ownership

| Test module | Primary evidence |
| --- | --- |
| `tests/test_run_qemu_result_precedence.py` | host, guest, explicit signal, success, syntax, and application |
| `tests/test_run_qemu_cleanup_failure_precedence.py` | first cleanup failure retained while later cleanup continues |
| `tests/test_run_qemu_first_signal_cleanup.py` | first handled signal remains authoritative |
| `tests/test_run_qemu_exit_cleanup_signal.py` | first signal during ordinary EXIT cleanup is retained |
| `tests/test_run_qemu_guest_before_cleanup_signal.py` | completed guest failure remains ahead of later cleanup signal |

## Remaining source facts

Before upstream submission, establish from canonical Salsa:

1. current full `master` commit SHA;
2. current `run_qemu.sh` blob identity;
3. equivalent active issue, branch, or merge request search;
4. current upstream-native test entry points;
5. clean rebase or identity proof from canonical `master` to candidate head.

The user has no repository-fetch task. The controlled mirror and candidate branch already exist.
