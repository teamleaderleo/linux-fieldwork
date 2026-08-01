# Source map — unit 05

## Upstream target

| Item | Exact value | Role |
| --- | --- | --- |
| Project | mmdebstrap | Upstream target |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` | Intended source of truth |
| Intended branch | `master` | Rebase target |
| Published Debian source | `1.5.7-3` | Current sid/forky source observed on 2026-08-01 |
| Published tag view | `debian/1.5.7-3`, abbreviated commit `6fde9997` | Published release marker; full live base remains unresolved |
| Target file | repository-root `run_qemu.sh` | Product source |
| Imported mirror | `upstream/mmdebstrap/run_qemu.sh` | Exact Linux Fieldwork source used by the canonical composition |
| Imported Git blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` | Exact base for local application |
| Imported SHA-256 | `da89b51df80786f4e379b2ba5b033aab6c4e1d7acc8ba17cf57e67159a32e300` | Byte receipt |
| Imported size | 2,029 bytes | Byte receipt |

Debian Sources lists the published `run_qemu.sh` at 2,029 bytes. This equal size is a useful compatibility clue and does not replace a live byte comparison.

## Canonical Linux Fieldwork lineage

| Carrier | Exact identity | Role and disposition |
| --- | --- | --- |
| Issue #269 | completed; canonical merge recorded | Original result-overwrite and cleanup lifecycle owner |
| Issue #297 | completed; selected event-order policy | Proved completed guest failure precedes a later cleanup-time signal |
| PR #270 | head `76ffad2ea25f03272c788d37de6232b6a0b287d7`; CI `30623610733` / 828 | Patches 1–2 and primary negative controls; closed unmerged as component evidence |
| PR #282 | head `e973546c350682e1175fa68fbf705c83487c2cf9`; CI `30624661338` / 844 | Patch 3 and ordinary-cleanup signal mechanism; closed unmerged as component evidence |
| PR #290 | final head `3843065077c233f9f8f8b3466873cad511c8d36f`; CI `30624235289` / 838 | Fixture-generation and exact-function extraction repair variant; superseded by the cleaner #282 head |
| PR #304 | head `0d5864c53badee91b403676ecc55e7aef5c38679`; CI `30625359304` / 854 | Patch 4 and losing `signal > guest` comparison; closed unmerged as policy evidence |
| PR #319 | head `2fe3f99364df29de217536dc35a4d03b10f49640`; base `782774b01002abf37878d834a54d0bbf8b226397`; merge `b196d6b45f496d8eb2d763922532ad257f24bba8` | Single canonical four-patch composition |
| PR #319 review | `4828231099` | Complete seventeen-file review selecting the final precedence order |
| PR #319 CI | run `30628645668`, job 889 | 276 passing repository tests on the exact head |

## Retained patch series

| Order | Packet path | Canonical source path | Git blob | Purpose |
| ---: | --- | --- | --- | --- |
| 1 | `patches/0001-preserve-primary-result.patch` | `investigations/run-qemu-result-precedence/0001-preserve-primary-result.patch` | `387b0e1d9ae0adb067a2efdc5177bf8e6814668d` | Separate EXIT and signal cleanup; preserve host, guest, and first cleanup failure |
| 2 | `patches/0002-retain-first-signal-through-cleanup.patch` | `investigations/run-qemu-result-precedence/0002-retain-first-signal-through-cleanup.patch` | `8f4713ab827eaf643a97ba0f9d0e9b190ab7cd49` | Prevent later handled signals from replacing the first or interrupting cleanup |
| 3 | `patches/0003-retain-signal-during-exit-cleanup.patch` | `investigations/run-qemu-result-precedence/0003-retain-signal-during-exit-cleanup.patch` | `227b2600851828d20861d191c1bdb54c0008ca10` | Retain the first signal during ordinary EXIT cleanup |
| 4 | `patches/0004-preserve-completed-guest-before-cleanup-signal.patch` | `investigations/run-qemu-result-precedence/0004-preserve-completed-guest-before-cleanup-signal.patch` | `3769c89a002511c09350a6a9735910eb53947d66` | Preserve completed guest failure before a later cleanup-time signal |

The packet copies are intended to remain byte-identical to these source blobs. Their local application receipt is in `artifacts/2026-08-01-apply-and-syntax.txt`.

## Canonical focused tests

| Test module | Primary evidence |
| --- | --- |
| `tests/test_run_qemu_result_precedence.py` | host, guest, explicit signal, ordinary success, and syntax/application behavior |
| `tests/test_run_qemu_cleanup_failure_precedence.py` | first cleanup failure wins while later cleanup continues |
| `tests/test_run_qemu_first_signal_cleanup.py` | first handled signal remains authoritative through cleanup |
| `tests/test_run_qemu_exit_cleanup_signal.py` | first signal during ordinary EXIT cleanup is retained |
| `tests/test_run_qemu_guest_before_cleanup_signal.py` | completed guest failure remains ahead of later cleanup-time signal |

These tests execute reduced real-`/bin/sh` fixtures and disposable directories. They do not execute QEMU, `debvm-run`, a guest image, mounts, networking, or root operations.

## Code ownership map

| Product region | Current behavior | Candidate owner |
| --- | --- | --- |
| initial temporary directory and signal state | `tmpdir` plus one cleanup-time signal slot | patches 1 and 3 |
| final result compilation | host, guest, signal, cleanup ordered selection | patches 1, 3, and 4 |
| ordinary EXIT handling | captures `$?`, records first INT/TERM, clears EXIT, enters finalizer | patches 1–3 |
| explicit INT/TERM handling | supplies 130/143, ignores later handled signals, clears EXIT, enters finalizer | patches 1–2 |
| cleanup actions | retain first failure and continue later actions | patch 1 |
| upstream command and guest workload | unchanged | outside unit |

## Missing source facts

The next worker must establish these from a live canonical Salsa checkout:

1. full `master` commit SHA;
2. exact `run_qemu.sh` Git blob and SHA-256;
3. whether the four packet patches apply without fuzz or offsets at the repository-root path;
4. any current equivalent issue, branch, or merge request;
5. current upstream test entry points covering `run_qemu.sh`.
