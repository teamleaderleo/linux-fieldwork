# Foundational systems deep-dive — 2026-08-03

## TL;DR

This round converted five public leads into exact-head Linux Fieldwork records.

The strongest immediate execution unit remains systemd vmspawn issue 43141: current source still contains the invalid no-userns call path and has a nearby real VM integration harness.

The strongest source-level conclusion is curl issue 22327: the reviewed Ceph Asio adapter consumes a one-shot readiness wait and does not re-arm it while curl's unchanged interest remains active. The repair owner is the adapter unless a reduced persistent-watcher reference later demonstrates a separate curl defect.

BuildKit issue 3267 is broader than the issue's single `.dockerignore` sentence: current conversion has both eager ignore access and unconditional final main-context materialization. Tests must cover both gates.

The two older lifecycle reports require different treatment. BuildKit issue 2855 predates substantial executor repairs and must be rerun on current head. systemd issue 42091 still has its reported source ingredients and needs a deterministic event-order/invariant test.

No upstream contact was made.

## Exact revisions

| Project | Canonical revision | Controlled fork state observed |
|---|---|---|
| Linux Fieldwork | base `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` | research branch created |
| systemd | `ac33190d1f66e870d511827cbed3ebeee2d704c2` | fork default head `6a863b4dc31adc49fdfdd5deba32ed1b115adda3`; canonical 18 ahead at observation |
| BuildKit | `275d6864ff0ce91a06225af5f5b012887bd257cf` | fork default head `df0761886a20e368d75e0aa6bb3f20874f58b692`; canonical 5 ahead at observation |
| curl | `c59b06c99ce1663560caf0147a11eb05c4b30689` | fork and canonical observed at same head |
| Ceph adapter | PR 58094 head `e88ba9657b7b8e9692d0bb1d20eb25b8dde6ee55` | read-only external source |

Default branches in controlled forks were not rewritten.

## Records created

### Target maps

- [`systemd`](../../targets/systemd/map.md)
- [`BuildKit`](../../targets/buildkit/map.md)
- [`curl`](../../targets/curl/map.md)

### Investigations

- [`systemd-vmspawn` unmapped bind and user-namespace entry](../../investigations/systemd-vmspawn-unmapped-bind-userns/README.md)
- [BuildKit unused local context loading](../../investigations/buildkit-unused-context-lazy-load/README.md)
- [Asio and libcurl multi-socket readiness re-arming](../../investigations/curl-asio-multi-socket-rearm/README.md)
- [BuildKit rootless cancellation and zombie ownership](../../investigations/buildkit-rootless-cancel-zombies/README.md)
- [systemd-logind VT release and controller-drop race](../../investigations/systemd-logind-vt-release-race/README.md)

## Ranked findings

## 1. curl/Asio adapter: source-contract answer reached

### Demonstrated

- curl's socket callback reports changed desired monitoring.
- curl suppresses callbacks when the desired socket action is unchanged.
- curl's libuv example uses a persistent watcher.
- Boost.Asio `async_wait()` is one-shot.
- the Ceph adapter's completion handler calls curl once and returns without another wait.

### Conclusion

The source sequence explains the report without requiring a curl regression. A persistent or generation-safe Asio watch must translate curl's continuing interest into repeated one-shot waits.

### Additional discriminators

- client-managed `CURL_POLL_REMOVE` must detach monitoring without assuming close;
- deliberate `operation_aborted` must not become a false socket error;
- `INOUT` and fd-number reuse require stale-completion protection.

### First execution

A local split-response server that requires two readable completions while curl interest remains unchanged.

## 2. systemd vmspawn: narrow current-head candidate

### Demonstrated

- regular binds can leave `userns_fd` invalid;
- current child code calls `namespace_enter()` unconditionally;
- `namespace_enter()` returns `EPERM` to an unprivileged caller with no child user namespace;
- subsequent mount setup is already guarded by valid descriptors;
- public bisect points to the commit that introduced the unconditional call.

### Candidate

Call `namespace_enter()` only when `userns_fd` is valid. Keep the general helper's capability enforcement unchanged.

### Required caution

Confirm the intended `block_dlopen()` hardening side effect separately. Do not preserve an invalid namespace operation merely to trigger unrelated helper hardening.

### First execution

Add the ordinary-user host-probe/guest-probe regression to the existing TEST-87 vmspawn harness, capture baseline failure, then test the descriptor guard across unmapped, translated, and foreign-UID paths.

## 3. BuildKit unused context: two lazy gates

### Demonstrated

- Docker ignore patterns are loaded at the beginning of stage dispatch;
- default ignore loading performs a main-context solve;
- the matcher only serves local source validation in the reviewed path;
- finalization calls `MainContext()` unconditionally even with no collected context paths.

### Candidate direction

- memoized ignore-pattern loading triggered by a reachable local source;
- explicit context-consumed state controlling final materialization.

### First execution

Use separate Dockerfile and main-context inputs. Make main-context access fail with a sentinel error. A metadata-only target must succeed; local `COPY` and context bind mounts must trigger the sentinel.

## 4. systemd logind VT race: current source still actionable

### Demonstrated

- bus handling is attached at normal event priority;
- the VT release signal source has no distinct priority in the reviewed code;
- controller drop restores VT mode immediately;
- the reviewed path has no explicit pending-release state.

### Design warning

A flag set only inside the signal callback cannot prevent the exact order where D-Bus dispatch runs first. Priority and state may need to work together, or restore may need a kernel-visible discriminator.

### First execution

Create deterministic queued-event orders and retain exact ioctl traces. Treat higher signal priority as a diagnostic before accepting it as a final protocol repair.

## 5. BuildKit rootless zombies: old report is now a regression specification

### Demonstrated

- no-process-sandbox uses the host PID namespace;
- current executor keeps runc alive while killing the contained process;
- current code retries kill and waits for runc exit;
- later commits specifically repaired runc reaping and open-stdin shutdown behavior;
- the public report predates those changes.

### First execution

Run a four-mode matrix: rootful/rootless crossed with default/no-process-sandbox, plus open-stdin and TTY controls. Record PID/PPID, namespace inode, cgroup, runc state, and repeated-solve behavior.

## Shared technical theme

Each investigation asks the same ownership questions at a different boundary:

- vmspawn: who decides whether a namespace transition exists;
- BuildKit context loading: when an input becomes part of the execution graph;
- curl/Asio: who maintains readiness interest after one event;
- BuildKit cancellation: who owns process termination and reaping after the client leaves;
- logind VT switching: who owns an in-flight kernel transition when controller cleanup races it.

The reusable review rule is:

> Identify the resource or transition owner, the event that transfers ownership, and the evidence that proves ownership ended.

## Recommended execution order

1. curl two-read standalone fixture — smallest and most decisive runtime proof.
2. systemd vmspawn TEST-87 regression — strongest bounded product candidate.
3. BuildKit sentinel-context tests — tests before interface design.
4. BuildKit current cancellation matrix — classify whether code work remains.
5. systemd VT deterministic event-order fixture — deepest environment-dependent work.

This order is based on discriminating evidence per unit of setup, not presumed project importance.

## Cross-project boundaries

- Do not update existing upstream issues with source-only conclusions without authorization.
- Do not create product patches before the first failing discriminator is retained.
- Do not rewrite controlled-fork default branches; use exact canonical-base research branches.
- Keep curl adapter work separate from curl library work unless a persistent-watcher reference fails.
- Keep systemd vmspawn namespace entry separate from generic namespace-helper hardening.
- Keep BuildKit graph input loading separate from rootless process cleanup.
- Keep display-manager timeouts separate from logind VT protocol repair.

## Evidence boundary

This round performed public source, issue, history, test-harness, and API-contract review. It did not compile the projects, launch a VM, start BuildKit, open test sockets, alter a VT, or run the proposed candidates. Source-supported conclusions and runtime-unverified hypotheses are labeled separately in each investigation.

## Authority

No canonical-project issue, pull request, comment, review, email, patch submission, or other external interaction was created or authorized.