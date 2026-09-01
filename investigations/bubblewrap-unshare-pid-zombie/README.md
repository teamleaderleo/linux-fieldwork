# Bubblewrap `--unshare-pid` monitor / namespace-init zombie

## TL;DR

Exact-current Bubblewrap main (`2f55bae38468d0c50cf5df87b1e481e882b63acb`, Bubblewrap 0.12.0) reproduces the helper-zombie symptom reported in upstream issue #697. With `--unshare-pid`, sandbox PID 1 reports the initial command's status through an eventfd and continues reaping. The outer monitor prioritizes that eventfd and can return before its SIGCHLD path reaps PID 1. Under a non-reaping adopter, the later PID 1 exit remains visible as a `[bwrap]` zombie.

A narrow candidate is proven on the exact source. After PID 1 reaps the initial command, and only on the existing eventfd PID-namespace path, it non-blockingly drains children that have already exited. If no descendants remain, PID 1 exits normally and the outer monitor reaps it. If a live descendant remains, the existing early-return behavior is preserved.

Final product-evidence head: `teamleaderleo/linux-fieldwork@7fc5f3c9a3a8ee89d2432f0ae5e760fdd14a6e1e`.

Authoritative run/job: `31490203503` / `93774626736` — success.

Artifact: `9101208976`, digest `sha256:d56d009dadd12382a1db02f8f5e370474ae9417ff2aef5966272309a50e06799`.

Internal Fieldwork issue: #553. Internal review PR: #557.

## Explain like I'm five

Bubblewrap creates a small helper as process 1 inside a new PID namespace. That helper watches the program the user actually asked to run.

```text
input:  bwrap --unshare-pid --dev-bind / / -- /bin/true
action: /bin/true exits; helper PID 1 reports success to outer bwrap
baseline result: outer bwrap exits first; helper exits next and can remain as a zombie
candidate result: with no remaining child, helper exits first and outer bwrap reaps it
```

When a real background child is still running, the candidate leaves the old behavior alone: outer `bwrap` returns immediately and helper PID 1 stays alive to reap the descendant.

## Why care

The surviving object is a Bubblewrap helper process. Upstream #697 reports `[bwrap]` remaining as a zombie after a short `--unshare-pid` invocation and gives a no-`--unshare-pid` control. A later report on that issue names Firefox/Glycin use of `--unshare-all`, which implies `--unshare-pid`, so the lifecycle edge reaches ordinary desktop callers as well as minimal containers.

The repair boundary has compatibility consequences. Bubblewrap has long allowed PID 1 to stay alive after the initial process exits because that initial process might be a launcher that forks a real application or daemon. A blocking outer wait would change that contract. The retained candidate fixes the no-descendant case without coupling outer-bwrap lifetime to a remaining descendant.

## Current state

- State: `REVIEW`
- Exact upstream source: `containers/bubblewrap@2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Upstream version: `0.12.0`
- Final product-evidence Fieldwork head: `7fc5f3c9a3a8ee89d2432f0ae5e760fdd14a6e1e`
- Authoritative focused run/job: `31490203503` / `93774626736` — success
- Artifact: `9101208976`
- Artifact digest: `sha256:d56d009dadd12382a1db02f8f5e370474ae9417ff2aef5966272309a50e06799`
- General Fieldwork CI on the product-evidence head: success
- Cleanup state: adopted fixture children are explicitly reaped after observation; privileged Docker fixtures use `--rm`
- Next safe action: human review of the bounded lifetime policy and candidate
- External-contact state: no upstream contact authorized or made

## Intent and precedent

### Current source has two completion boundaries

At the exact source head, `event_fd` is created when `--unshare-pid` is active and `--as-pid-1` is absent. After namespace setup, Bubblewrap forks the command: the parent becomes sandbox PID 1 and runs `do_init()`, while the child execs the requested command as PID 2.

`do_init()` waits for children. When the initial command exits, it stores that exit status and writes `initial_exit_status + 1` to `event_fd`. It then continues waiting until no children remain.

The outer `monitor_child()` polls the eventfd and a SIGCHLD signalfd. It deliberately reads the eventfd first so the initial command's result wins if command and PID 1 exits happen close together. When the eventfd supplies a value, the monitor returns immediately. The later SIGCHLD/`waitpid()` path is therefore skipped on that return path.

Primary source:

- https://redirect.github.com/containers/bubblewrap/commit/2f55bae38468d0c50cf5df87b1e481e882b63acb
- `bubblewrap.c::monitor_child()`
- `bubblewrap.c::do_init()`

### Upstream runtime report matches this owner

Upstream issue #697 reports Bubblewrap 0.11.0 leaving a `[bwrap]` zombie after a short `--unshare-pid` command in a privileged Alpine container whose PID 1 does not reap the orphan. The issue remains open.

- https://redirect.github.com/containers/bubblewrap/issues/697

### Background descendants are an intentional compatibility boundary

Older lifecycle discussion in issue #105 explains why Bubblewrap cannot assume the initial process is the whole application. With `--unshare-pid`, sandbox PID 1 may need to remain alive to reap descendants after the initial process exits.

- https://redirect.github.com/containers/bubblewrap/issues/105

That precedent rules out treating a blocking `waitpid()` in the outer monitor as a mechanical cleanup fix. The candidate instead distinguishes “no descendants remain” from “a live descendant remains.”

## Question

Can exact-current Bubblewrap avoid orphaning the namespace PID 1 helper after a short `--unshare-pid` command while preserving the established immediate outer return when a real descendant remains, and while preserving the initial command's exit-status representation?

## Source

- Project: `containers/bubblewrap`
- Requested revision: current default branch at final verification
- Resolved commit: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Version: `0.12.0`
- Candidate patch: `0001-delay-exit-event-while-no-descendants-remain.patch`
- Upstream tree identity was fetched and checked by exact Git SHA in CI
- No upstream fork branch or upstream interaction was created

A final upstream commit search after candidate validation still returned `2f55bae38468d0c50cf5df87b1e481e882b63acb` as current main.

## Environment

Authoritative hosted execution:

- Host runner: Ubuntu 24.04.4 LTS, x86_64
- Host kernel: `6.17.0-1020-azure`
- Docker client/server: `28.0.4` / `28.0.4`
- Product fixture: privileged disposable `ubuntu:24.04` container
- Compiler: GCC 13.3.0
- Meson: 1.3.2
- Bubblewrap: 0.12.0 built from exact upstream SHA
- Python fixture: Python 3

The ordinary hosted runner has `kernel.unprivileged_userns_clone=1` and `user.max_user_namespaces=63838`, but Bubblewrap still stops at `setting up uid map: Permission denied`. That result is retained as a capability boundary. The authoritative product execution therefore runs inside the privileged disposable container.

## Baseline behavior

Exact current source under the synthetic subreaper harness:

```text
pid-helper: bwrap_rc=0 adopted_children=[(2536, 'Z (zombie)', 'bwrap')]
as-pid-1-control: bwrap_rc=0 adopted_children=[]
no-pidns-control: bwrap_rc=0 adopted_children=[]
exit-42: bwrap_rc=42 expected_rc=42 adopted_children=[(2543, 'Z (zombie)', 'bwrap')]
signal-term: bwrap_rc=143 expected_rc=143 adopted_children=[(2546, 'Z (zombie)', 'bwrap')]
background-child: bwrap_rc=0 elapsed=0.002s immediate_adopted=[(2549, 'S (sleeping)', 'bwrap')] final_adopted=[(2549, 'Z (zombie)', 'bwrap')]
```

The controls distinguish the helper/eventfd path. The exit-status cases also show that the zombie is independent of whether the initial command exits zero, exits nonzero, or terminates by signal.

## Candidate

The candidate changes only the existing `event_fd != -1` path in `do_init()`.

After PID 1 reaps the initial command:

1. call `waitpid(-1, ..., WNOHANG)` until no already-exited child remains;
2. if `waitpid()` returns `0`, a live descendant remains, so write the existing eventfd notification and preserve immediate outer return;
3. if the drain reaches `ECHILD`, no descendants remain, so omit the eventfd write and let PID 1 return normally;
4. the outer monitor then receives SIGCHLD, calls `waitpid()` for PID 1, and returns the already-preserved initial exit status.

Scoping the drain inside `event_fd != -1` leaves `do_init()` paths used only for `--lock-file` or `--sync-fd` in their original ordering.

The candidate deliberately leaves the later orphan-helper outcome open when a real descendant outlives outer `bwrap`. Eliminating that outcome while retaining immediate outer return requires a different ownership policy.

## Reproduction

Synthetic ordering model:

```sh
python3 investigations/bubblewrap-unshare-pid-zombie/repro_subreaper_zombie.py --model
```

Exact Bubblewrap baseline:

```sh
python3 investigations/bubblewrap-unshare-pid-zombie/repro_subreaper_zombie.py \
  --bwrap /path/to/exact-current/bwrap
```

Candidate expectation:

```sh
python3 investigations/bubblewrap-unshare-pid-zombie/repro_subreaper_zombie.py \
  --bwrap /path/to/candidate/bwrap \
  --expect-short-clean
```

The hosted workflow builds both exact trees, runs the probes in privileged disposable containers, then runs Bubblewrap's upstream test suite against baseline and candidate under the same fixture.

## Results

### Synthetic model

The standalone Linux subreaper model repeatedly observes the delayed helper as `Z` after the outer process exits, then explicitly reaps it.

### Exact-current reproduction

The short `--unshare-pid` path reproduces the adopted `[bwrap]` zombie. `--as-pid-1` and no-PID-namespace controls remain clean.

### Candidate short-command result

```text
pid-helper: bwrap_rc=0 adopted_children=[]
as-pid-1-control: bwrap_rc=0 adopted_children=[]
no-pidns-control: bwrap_rc=0 adopted_children=[]
```

The no-descendant helper is reaped before outer `bwrap` returns.

### Exit-status and signal representation

Candidate:

```text
exit-42: bwrap_rc=42 expected_rc=42 adopted_children=[]
signal-term: bwrap_rc=143 expected_rc=143 adopted_children=[]
```

The candidate preserves ordinary nonzero exit status and Bubblewrap's `128 + signal` representation.

### Background-descendant discriminator

Candidate:

```text
background-child: bwrap_rc=0 elapsed=0.003s immediate_adopted=[(2549, 'S (sleeping)', 'bwrap')] final_adopted=[(2549, 'Z (zombie)', 'bwrap')]
```

The outer process still returns immediately while `sleep 3` remains. Sandbox PID 1 remains alive to reap it. After that descendant exits, the helper can still become an adopted zombie under the synthetic non-reaping parent. This is the explicitly retained compatibility boundary.

### Upstream suite comparison

Baseline and candidate both produced:

```text
test-utils                OK   26 subtests passed
test-seccomp.py           SKIP
test-run.sh               OK   56 subtests passed
test-specifying-pidns.sh  OK
test-specifying-userns.sh OK

Ok:      4
Fail:    0
Skipped: 1
```

The seccomp test is skipped in this fixture for both baseline and candidate.

### Gate-owner corrections during investigation

Two failed hosted gates were evidence/fixture problems rather than candidate failures:

- the first patch carrier had invalid unified-diff hunk counts and failed `git apply`; the carrier was repaired without changing candidate behavior;
- the first upstream-suite container lacked `pkg-config`; adding that build dependency allowed unchanged baseline/candidate suite logic to run and pass.

Both failures were classified before product code was changed.

## Interpretation

The current defect is a lifecycle ownership gap between command completion and helper reap completion.

The candidate repairs the bounded no-descendant case at the owning PID 1/eventfd boundary. It makes the eventfd early-return path conditional on a reason for early return: at least one live descendant still exists. If no descendants exist, allowing PID 1 to finish first gives the outer monitor an ordinary child it can reap without delaying any useful descendant.

The result is narrower than “always wait for PID 1” and narrower than “kill the PID namespace when the initial command exits.” Those alternatives change established descendant behavior.

Inside the tested premises, the candidate survives the distinguishing controls, exit-status cases, background-child lifetime discriminator, exact-source build, cleanup/rerun behavior, and Bubblewrap's upstream suite.

## Evidence boundary

Established:

- exact-current Bubblewrap main at `2f55bae38468d0c50cf5df87b1e481e882b63acb` reproduces the short-command helper zombie under a non-reaping subreaper;
- the relevant owner is `do_init()` / `monitor_child()` eventfd lifecycle coordination;
- the candidate eliminates the no-descendant adopted helper zombie;
- ordinary exit `42` and SIGTERM representation `143` are preserved;
- immediate outer return with a live background descendant is preserved;
- baseline and candidate upstream suites match in the authoritative fixture.

Limits:

- one hosted x86_64 Ubuntu kernel family was executed;
- no AArch64 runtime execution;
- no Flatpak, Glycin, Firefox, Steam, Bottles, or other desktop integration execution;
- the seccomp test is skipped in the suite fixture for both baseline and candidate;
- the candidate intentionally does not eliminate the eventual helper zombie after a real descendant outlives outer `bwrap`;
- no claim is made that every host exposes the zombie, because visibility depends on the orphan adopter's reaping behavior;
- no upstream interaction occurred.

Reopen this bounded decision if a new result shows that the eventfd drain changes descendant lifetime, exit status, signal representation, lock/sync behavior, or another supported PID-namespace mode inside these premises.

A separate successor question is warranted if the desired policy becomes “outer bwrap returns immediately and no helper can ever become an orphan after descendants finish.” That requires a different ownership mechanism.

## Next step

Human review should choose whether the bounded policy is the desired one:

- retain the candidate as the local fix for the no-descendant case;
- request another compatibility discriminator;
- choose a broader lifetime policy as a separate design;
- prepare an upstream packet only after explicit authorization.

Current recommendation: retain this narrow candidate for review. The exact-current defect, repair mechanism, compatibility boundary, and remaining limitation are all explicit in the retained evidence.

## Authority

No upstream issue, pull request, email, comment, review, or patch submission was created by this investigation. Existing upstream issues were read only. External contact remains unauthorized pending an explicit human decision.
