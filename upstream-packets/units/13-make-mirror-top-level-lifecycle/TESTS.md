# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Public upstream base | `josch/mmdebstrap` `main` at `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Public/imported source blob | `make_mirror.sh` `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Canonical candidate carrier | PR #224 head `13b3c529e983b3ad967725f99f4e31d867fa4742` |
| Canonical candidate patch blob | `25f9474945a6eb0efa52415f1fcd18e784655d59` |
| Linux Fieldwork unit branch base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Platform/distribution for retained CI | Linux Fieldwork hosted Linux runner; exact image recorded by workflow run |
| Shell/runtime | real `/bin/sh`; Python unittest harness |
| Privilege boundary | disposable unprivileged processes, files, directories, and symlinks |
| Network/APT/QEMU | excluded from focused tests |

## Baseline reproducer

### Command

```sh
python3 -m unittest -v \
  tests/test_make_mirror_signal_exit.py
```

The module constructs the exact baseline post-readiness cleanup-only trap and delivers parent-PID-only TERM while the shell is waiting for a foreground child.

### Expected distinguishing result

The baseline demonstrates the defect by running cleanup, resuming later work, running EXIT cleanup again, and returning status 0.

### Observed result

- status: baseline harness owner exits 0 after TERM;
- stdout/stderr: focused unittest passes because the losing result is expected;
- changed state: later-work marker exists; cleanup count is two;
- surviving processes/files/resources: proxy is terminated by trap, but reaping is implicit in the baseline contract;
- receipt: PR #159 exact-head CI `30578159552`, retained unchanged by #205 and composed into #224.

## Candidate reproducer

### Commands

```sh
python3 -m unittest -v \
  tests/test_make_mirror_signal_exit.py

python3 -m unittest -v \
  tests/test_make_mirror_proxy_launch_ownership.py
```

The tests apply the exact retained patch to a disposable complete source copy, require successful `/bin/sh -n`, then execute real-shell reduced lifecycle cases.

### Expected result

- INT/QUIT/TERM exit 130/131/143 after owner cleanup;
- later work stays absent;
- each current proxy is signaled, waited, and cleared;
- ordinary unsignaled reruns return 0;
- both launch-to-PID windows retain the first signal through child registration;
- launch one performs one owner cleanup, one proxy stop, and zero signal-time cache deletion calls;
- launch one's immediate rerun removes retained pre-readiness state through startup preflight;
- launch two performs one owner cleanup and one private-cache deletion;
- TERM before PID registration followed by INT after registration still returns 143;
- late cleanup preserves a cache already selected by `shared/cache -> $newcache`.

### Observed result

- status: 10/10 focused cases passed twice consecutively on final PR #224 tree;
- stdout/stderr: all unittest cases green; complete candidate `/bin/sh -n` green;
- changed state: private state removed only under the correct ownership state; active published cache retained;
- surviving processes/files/resources: no candidate proxy survives; immediate clean reruns succeed;
- receipts: exact-head Linux Fieldwork CI `30586490855`; complete five-file review `4823717630`; PR #224 head `13b3c529e983b3ad967725f99f4e31d867fa4742`.

## Matrix

| Case | Baseline or predecessor | Candidate | Exact test | Result identity |
| --- | --- | --- | --- | --- |
| Parent-only TERM during foreground wait | cleanup, continuation, second cleanup, status 0 | cleanup once, no later marker, status 143 | `test_make_mirror_signal_exit.py` | CI `30578159552`, retained in #224 |
| Ordinary success | raw stop and EXIT trap semantics | proxy stopped/waited, later work completes, status 0 | same | immediate rerun green |
| Published-cache cleanup | broad failed-cache cleanup can own active result | active symlink clears private ownership; cache remains | same | publication regression green |
| First proxy launch before PID registration | new child can exist without owned PID | first signal retained, PID registered, child reaped, status 143 | `test_make_mirror_proxy_launch_ownership.py` | final #224 matrix green |
| Second readonly proxy launch before PID registration | same ownership gap | same launch helper and first-signal rule | same | final #224 matrix green |
| Competing TERM then INT | intermediate candidate can let INT overtake pending TERM | first TERM stays authoritative | same | status 143 |
| Launch-one cache ownership | intermediate test forced deletion ownership `yes` | ownership `no`; zero signal-time deletion calls | same | independent review repair green |
| Launch-one rerun | retained state can interfere | startup preflight removes retained alternate state; rerun returns 0 | same | final #224 matrix green |
| Launch-two cache ownership | private cache is already owned | one private-cache deletion | same | final #224 matrix green |
| Proxy reaping | raw `kill`; wait implicit | `wait` always attempted; PID cleared | both modules | no surviving child |
| QEMU temporary cleanup | trap text couples operations | cleanup flag enables only during active QEMU temp state | source assertions and reduced harness | final review accepted |
| `update_cache()` cleanup-time signal | separate pipeline-subshell boundary | unit 14 candidate in PR #324 | separate tests | excluded from unit 13 candidate |

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Current-source zero-fuzz application | command in “Patch application and rebase” below | NOT RUN in this pass: repository retrieval failed at DNS resolution | packet branch |
| Complete shell syntax on fresh public source | `/bin/sh -n make_mirror.sh` after patch | NOT RUN in this pass for same environment reason | packet branch |
| Focused retained tests on unit branch | two unittest commands above | NOT RUN in this pass for same environment reason | packet branch |
| Full upstream mirror creation | `./make_mirror.sh` | NOT RUN: network/APT/QEMU/privilege-heavy gate | future controlled upstream candidate |
| Upstream coverage suite | `CMD=./mmdebstrap ./coverage.sh` | NOT RUN: depends on mirror/cache preparation and broader candidate branch | future controlled upstream candidate |
| Complete upstream diff review | compare candidate branch to exact upstream base | NOT RUN: controlled fork/branch absent | `NEEDS FORK` |

## Linux Fieldwork retained gates

| Gate or fixture | Exact command/run | Result | Artifact/digest |
| --- | --- | --- | --- |
| First repaired parent lifecycle | PR #159 CI `30578159552` | PASS | head `ebda4974541995a236f7fb791f8019b31d10f4b9` |
| Current-main parent restack | PR #205 CI `30579821292` | PASS | head `ac2680e0dc92b497f6ada5622b50e7f41ebb56af` |
| Current-main execution carrier | PR #201 CI `30579465025` | PASS; focused four-test matrix twice | exact #159/#205 blobs |
| Final top-level launch/ownership matrix | PR #224 CI `30586490855` | PASS | head `13b3c529e983b3ad967725f99f4e31d867fa4742` |
| Final complete-diff review | PR #224 review `4823717630` | PASS; no remaining source/test defect in declared top-level scope | same head |
| Current public source identity | public Forgejo and Debian dgit lookup, 2026-08-01 | MATCH | blob `6c4be092edcf23b56b63a3befe238c099c45f590` |
| Packet branch creation | compare `main...upstream/unit-13-make-mirror-top-level-lifecycle` | branch started identical | base `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |

## Patch application and rebase

- public base identity: `77ec9be5417ee44c96343d2347145585da1b1f94`;
- source blob identity: `6c4be092edcf23b56b63a3befe238c099c45f590`;
- packet patch: `patches/0001-make-mirror-top-level-signal-proxy-ownership.patch`;
- canonical patch blob: `25f9474945a6eb0efa52415f1fcd18e784655d59`;
- intended command:

```sh
workdir=$(mktemp -d)
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap.git "$workdir/mmdebstrap"
git -C "$workdir/mmdebstrap" checkout 77ec9be5417ee44c96343d2347145585da1b1f94
[ "$(git -C "$workdir/mmdebstrap" hash-object make_mirror.sh)" = \
  6c4be092edcf23b56b63a3befe238c099c45f590 ]
patch --batch --forward --fuzz=0 -d "$workdir/mmdebstrap" -p1 \
  -i "$PWD/upstream-packets/units/13-make-mirror-top-level-lifecycle/patches/0001-make-mirror-top-level-signal-proxy-ownership.patch"
/bin/sh -n "$workdir/mmdebstrap/make_mirror.sh"
```

- historical fuzz/offset result: exact #224 patch dry-run passed with zero fuzz;
- current-pass result: unexecuted because clone failed before retrieval;
- conflict resolution: none selected;
- complete diff reviewed: final #224 five-file carrier reviewed at exact head; fresh upstream candidate diff pending;
- active overlap searched: public Forgejo issues/PRs searched 2026-08-01; no visible equivalent carrier found.

## Cleanup and rerun

Retained focused tests use temporary directories, test-created shell processes, `sleep` proxy stand-ins, files, and symlinks. They signal and wait only for test-created processes. Final #224 receipts require no surviving proxy and an immediate unsignaled rerun that returns 0.

This pass created `/tmp/lf-unit13` before repository retrieval. The clone command failed before a checkout existed. No repository, process, socket, mount, container, mirror cache, or generated candidate source remained. The empty temporary parent directory may be removed by any later local runner; it contains no source or evidence.

## Tests not run

- fresh zero-fuzz application to upstream commit `77ec9be5417ee44c96343d2347145585da1b1f94`;
- fresh `/bin/sh -n` on the patched public source;
- focused unittests on the current packet branch;
- full `./make_mirror.sh` network mirror build;
- `CMD=./mmdebstrap ./coverage.sh`;
- process-group signal delivery;
- HUP handling;
- TERM-to-KILL escalation;
- proxy that permanently ignores TERM;
- hostile descendants;
- full QEMU lifecycle under cancellation;
- a controlled-fork compare and contribution-host CI.

## Failure classification

### Current-pass local clone failure

Command began with:

```sh
git clone --depth 1 --branch main \
  https://github.com/teamleaderleo/linux-fieldwork.git /tmp/lf-unit13/repo
```

Observed first distinguishing error:

```text
fatal: unable to access 'https://github.com/teamleaderleo/linux-fieldwork.git/':
Could not resolve host: github.com
```

Classification: environment/network DNS failure before repository retrieval. It provides no candidate result.

### Historical red runs retained from #159/#224

- malformed unified-diff hunk counts: patch packaging owner;
- source-tree/runtime directory collision: fixture owner;
- retained top-level trap text missed by weak assertion: evidence assertion owner;
- active published cache still classified as private: product lifecycle owner, repaired;
- ordinary traps restored before pending first-signal dispatch: product first-signal owner, repaired;
- first-launch fixture granted post-readiness deletion ownership: fixture/source-fidelity owner, repaired.

## Final evidence statement

The retained exact-head matrix establishes that the canonical top-level patch converts cleanup-only signal handling into terminating owner cleanup, explicitly reaps each owned proxy, closes both launch-to-PID registration windows, preserves the first signal, applies cleanup only under real ownership, protects an active published cache, suppresses later work, and permits immediate unsignaled reruns.

The current public source blob still matches the imported source exactly. Fresh application and execution remain the first incomplete gate because this pass's local runner could not resolve repository hosts. Full mirror, APT, QEMU, escalation, and process-group behavior remain outside the executed evidence.
