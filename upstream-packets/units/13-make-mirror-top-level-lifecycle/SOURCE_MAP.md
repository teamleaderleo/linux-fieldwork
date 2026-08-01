# Source map

## Upstream source identity

Search and source check date: 2026-08-01.

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | `make_mirror.sh` in `https://gitlab.mister-muffin.de/josch/mmdebstrap` | `main` head `77ec9be5417ee44c96343d2347145585da1b1f94`; file blob `6c4be092edcf23b56b63a3befe238c099c45f590` | Public source still contains the cleanup-only top-level traps, raw proxy stops, and launch/`$!` intervals addressed by this unit. |
| Debian source mirror | `https://browse.dgit.debian.org/mmdebstrap.git/tree/make_mirror.sh` | blob `6c4be092edcf23b56b63a3befe238c099c45f590` | Byte identity matches Linux Fieldwork's imported source blob recorded by PR #205. |
| Linux Fieldwork imported source | `upstream/mmdebstrap/make_mirror.sh` | blob `6c4be092edcf23b56b63a3befe238c099c45f590` | Intentionally unchanged; patches are retained separately. |
| Adjacent implementation | `make_mirror.sh:update_cache()` | same source blob | Pipeline-subshell lifecycle. Owned by unit 14; PRs #305/#324 are boundary evidence here. |
| Upstream tests | `make_mirror.sh`, `coverage.sh`, `coverage.py` | upstream `main` head above | Upstream README names `./make_mirror.sh` followed by `CMD=./mmdebstrap ./coverage.sh`; no focused signal test exists in the public tree. |
| Contribution instructions | upstream `README.md` and Forgejo issue/PR surfaces | upstream `main` head above | Bugs route to the project issue tracker. A controlled fork is still required before any authorized submission. |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Status |
| --- | --- | --- | --- |
| Issue #157 | closed 2026-07-30 | Original cleanup-only trap defect and bounded expected behavior | Historical owner |
| PR #159 | `ebda4974541995a236f7fb791f8019b31d10f4b9` | First complete top-level status, cleanup, reaping, rerun, and publication candidate | Superseded by #205 then #224 |
| PR #205 | head `ac2680e0dc92b497f6ada5622b50e7f41ebb56af`; merge `69a16e988a37af957c4ba8eb5f2c36e396827fe4` | Clean current-main restack of #159; post-merge review found launch/PID gaps | Component evidence |
| PR #224 | head `13b3c529e983b3ad967725f99f4e31d867fa4742`; merge `386f5c8dbb01e5de1af45ac0eb325ee8567722e3` | Closes both proxy launch-to-PID windows, retains first signal, corrects ownership-state tests | Canonical top-level carrier |
| PR #305 | `0a6b9cc404bcc5e463964be7cbcf74d710528d86` | Historical `update_cache()` cleanup-time signal successor | Adjacent; superseded by #324 |
| PR #324 | head `0906573b434710032f44807bfb5d6bb017a510f6`; merge `404540e46b35df682f1fc006bdadf837aafb1752` | Current-main `update_cache()` cleanup-time signal carrier | Adjacent unit 14 evidence |
| Canonical retained patch on `main` | blob `25f9474945a6eb0efa52415f1fcd18e784655d59` | Exact #224 product patch | Canonical source candidate |
| Unit packet copy | `patches/0001-make-mirror-top-level-signal-proxy-ownership.patch` | Review-local copy of the canonical retained patch | Current packet |

## Candidate code

| File | Lines or symbols | Change | Owning patch |
| --- | --- | --- | --- |
| `make_mirror.sh` | top-level proxy owner near first launch | Add owner state, terminating signal policy, child stop/wait, and launch-window first-signal retention | `0001-make-mirror-top-level-signal-proxy-ownership.patch` |
| `make_mirror.sh` | first readiness transition | Begin private-cache deletion ownership only after readiness | same patch |
| `make_mirror.sh` | normal first proxy stop | Route through idempotent `stop_proxy()` | same patch |
| `make_mirror.sh` | QEMU readonly proxy launch | Route through `launch_proxy()` and preserve first signal through PID registration | same patch |
| `make_mirror.sh` | QEMU temporary-directory lifecycle | Track temporary cleanup ownership separately | same patch |
| `make_mirror.sh` | publication/EXIT lifecycle | Preserve a cache already selected by `shared/cache -> $newcache` | same patch |

## Candidate tests

| File | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| `tests/test_make_mirror_signal_exit.py` | real `/bin/sh` reduced owner lifecycle | parent-only TERM cleans, resumes later work, cleans again, and exits 0 | exits 143, omits later work, cleans once, reaps proxy; ordinary rerun succeeds; published cache survives |
| `tests/test_make_mirror_proxy_launch_ownership.py` | stopped-owner controls for both launch/registration intervals | newly started proxy can escape ownership; early test version overclaimed cache deletion | first signal wins, proxy is registered then reaped, launch-one deletion ownership stays `no`, launch-two ownership is `yes`, reruns succeed |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-13-make-mirror-top-level-lifecycle`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS FORK`
- Canonical retained patch: `investigations/make-mirror-signal-exit/0001-preserve-signal-exit-status.patch`
- Packet patch copy: `patches/0001-make-mirror-top-level-signal-proxy-ownership.patch`
- Patch application command:

```sh
patch --batch --forward --fuzz=0 -p1 \
  -i upstream-packets/units/13-make-mirror-top-level-lifecycle/patches/0001-make-mirror-top-level-signal-proxy-ownership.patch
```

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| Ordinary top-level exit cleanup | shared cleanup-only trap text | top-level shell through `cleanup_owner()` | #159/#205 regression and #224 composition |
| INT/QUIT/TERM result | cleanup action returns to shell flow | `signal_exit()` exits 130/131/143 after cleanup | baseline/candidate signal matrix |
| Proxy child lifetime | raw `kill`; reaping implicit | `stop_proxy()` signals, waits, and clears PID | focused regression and source review |
| Signal during proxy launch before `$!` registration | no owner for the new child | `handle_launch_signal()` records first status; dispatch waits for PID ownership | #224 competing-signal control |
| First-launch cache deletion | trap text can imply broad cleanup | ownership remains `no` until readiness; startup preflight removes retained state on rerun | #224 ownership review repair |
| Second-launch private-cache deletion | top-level trap | top-level `cleanup_owner()` while ownership is `yes` | #224 ownership matrix |
| QEMU temporary directory | trap text | `CLEANUP_TMPDIR` flag under top-level owner | #159/#224 source review |
| Published cache | vulnerable to late generic cleanup | symlink identity clears private ownership and preserves active cache | #159 publication regression retained by #224 |
| `update_cache()` APT root | subshell trap also targets parent proxy | unit 14 patch confines cleanup to the subshell-owned APT root | PRs #305/#324; excluded here |

## Overlap and current upstream state

On 2026-08-01 the public Forgejo repository showed `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`. The `make_mirror.sh` file still had blob `6c4be092edcf23b56b63a3befe238c099c45f590`, identical to the imported Linux Fieldwork source. Searches of the public issue and pull-request surfaces for `make_mirror`, signal, proxy, trap, and cancellation found no visible equivalent carrier. The project showed six open issues, none describing this lifecycle defect.

The source identity result makes the retained patch current at the byte level. Exact zero-fuzz application and executable rerun against a newly retrieved public checkout remain required because the local execution environment could not resolve repository hosts during this pass.

## Files deliberately not changed

- `upstream/mmdebstrap/make_mirror.sh`: retained-patch workflow keeps imported source unchanged.
- `make_mirror.sh:update_cache()`: separate process owner and separate unit 14 patch sequence.
- `caching_proxy.py`: no proxy implementation defect was selected.
- `run_qemu.sh`: adjacent deferred-trap behavior has a terminating cleanup function and belongs to unit 05.
- upstream repository, issue tracker, pull-request surface, and email: external contact remains unauthorized.
