# LF-SCOUT-ROOT-01 — Chrootless `DPKG_ROOT` containment

## In simple words

The target package itself behaved correctly: its files, dpkg database entries, logs, and `update-alternatives` links stayed beneath the selected root. Install, reinstall, purge, install-after-purge, and two complete imported `mmdebstrap` runs all succeeded.

The host still participated in package-management side effects. On the GitHub Ubuntu runner, host dpkg configuration launched `/usr/lib/needrestart/dpkg-status` during target-root package operations. That program attempted to update `/run/needrestart/unpacked`; the runner's unprivileged UID blocked the write. Each imported `mmdebstrap` run also connected successfully to the host system D-Bus socket at `/run/dbus/system_bus_socket`.

**Decision: `promote`.** LF-02 defines host service actions as a promotion signal. The evidence shows repeatable host restart-management and D-Bus activity even though target package state remained clean and every attempted host marker write failed.

## Scout identity and home lane

- Scout-ID: `LF-SCOUT-ROOT-01`
- Home lane: `LF-02`
- Assignment: issue `#11`
- Working branch: `scout/lf-scout-root-01/lf-02-dpkg-root-containment`
- Pull request: `#21`
- Assigned reviewer: `LF-SCOUT-DEB-02`
- Cross-review duty: review `LF-SCOUT-PROC-01` on LF-23 after its `READY FOR REVIEW` post

## Exact source or package boundary

### Imported source

- Project: Debian `mmdebstrap`
- Imported path: `upstream/mmdebstrap/`
- Imported executable version: `1.5.7`
- Requested revision: `debian/1.5.7-3`
- Resolved upstream commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Repository import commit: `51c8480d7e61b3e31d74f69864042a3fc8c1d772`
- Source metadata: `upstream/mmdebstrap/.linux-fieldwork-source.json`
- Imported executable blob used for source reading: `dfb5e37b68271a46b9e75128cdd85975fbb383a1`

The branch also contains the repository's separate explicit-`TMPDIR` candidate. That candidate leaves the chrootless dpkg call path examined here unchanged.

### Package fixture

- Package: `lf-fieldwork-probe`
- Version: `1.0`
- Architecture: `all`
- Dependencies: none
- Hosted archive size: `1018` bytes
- Hosted archive SHA-256: `e0c7d467562e79f7e605eb973d7dec385d4910a0a8737a352ba453c0feaab6e8`
- Fixture source: `artifacts/fixture/`

The fixture contains one payload at `/usr/lib/lf-fieldwork-probe/tool` and four maintainer scripts:

- `preinst` records `DPKG_ROOT`, working directory, UID/GID, and interpreter;
- `postinst` records the same values, prepares target alternatives directories, and calls `update-alternatives --install`;
- `prerm` calls `update-alternatives --remove`;
- `postrm` records its phase.

This dependency-free package gives visible script, payload, dpkg database, and alternatives effects while keeping repository and network inputs out of the package boundary.

## Environment and privileges

### Local direct-dpkg run

- Date: 2026-07-30
- Runner: disposable Debian 13 container
- Kernel: Linux `6.12.13`, x86_64
- Package-action UID/GID: `65534:65534` (`nobody`)
- `dpkg`: `1.22.22`
- `apt`: `3.0.3`
- `update-alternatives`: `1.22.22`
- Network access: unavailable
- Target: `/tmp/lf-02-work/target`

The local image lacked the Ubuntu `needrestart` dpkg status logger. It provided the clean comparison case: target package effects stayed contained and the host sentinels remained unchanged.

### GitHub-hosted imported-source run

- Workflow run: `30515782245`
- Artifact ID: `8748803333`
- Artifact digest: `sha256:6ab07c15205d33897ec3a58f4781171547f35ec8deb14714c9dce578991ce86f`
- Runner: GitHub-hosted Ubuntu `24.04.4 LTS`
- Kernel: Linux `6.17.0-1020-azure`, x86_64
- UID/GID: `1001:1001` (`runner`)
- `dpkg`: `1.22.6`
- `apt`: `2.8.3`
- `update-alternatives`: `1.22.6`
- `strace`: `6.8`

Relevant host dpkg configuration:

```text
/etc/dpkg/dpkg.cfg.d/needrestart:
status-logger=(test -x /usr/lib/needrestart/dpkg-status && /usr/lib/needrestart/dpkg-status || cat > /dev/null)
```

Retained summaries are under `artifacts/hosted-results/`. The raw workflow artifact contains commands, stdout/stderr, target trees, script logs, host fingerprints, classifications, and all per-process traces.

## Source and test map

The imported call path is:

1. `setup()` performs hooks, apt setup/download, extraction, and installation.
2. `setup()` calls `run_essential()` before `run_install()`.
3. In chrootless mode, `run_essential()` invokes host `dpkg` with:
   - `--force-not-root`
   - `--force-script-chrootless`
   - `--root=<target>`
   - `--log=<target>/var/log/dpkg.log`
4. In chrootless mode, `run_install()` invokes host `apt-get` with dpkg options carrying the same root and script-chrootless flags.
5. `run_progress()` forks and directly executes the requested host command.
6. `dpkg --force-script-chrootless` runs maintainer scripts with host executables while exporting `DPKG_ROOT`.
7. Host `/etc/dpkg/dpkg.cfg*` remains an input because dpkg reads configuration before applying command-line root options.

Relevant imported source ranges in `upstream/mmdebstrap/mmdebstrap`:

- progress fork and direct exec: approximately lines `1847-1902`;
- setup order and handoff: approximately lines `2978-2985`;
- apt state rooted at the target: approximately lines `3085-3112`;
- direct essential dpkg command: approximately lines `3918-3963`;
- chrootless apt/dpkg options: approximately lines `4056-4065`;
- root-without-fakeroot safety check: approximately lines `6051-6064`;
- documented chrootless host dependency warning: approximately lines `8187-8201`.

## Probe design and distinguishing outcomes

### Direct dpkg probe

The runner exercises the exact direct dpkg boundary through four phases:

1. install;
2. reinstall over installed state;
3. purge;
4. install after purge.

Each phase runs under `strace -ff -yy -e trace=%file,%process,%network`. The probe checks payloads, package status, alternatives state, script observations, cleanup, and host fingerprints.

### Imported `mmdebstrap` probe

The imported executable runs twice into fresh directories with:

```sh
upstream/mmdebstrap/mmdebstrap \
  --mode=chrootless \
  --variant=custom \
  --format=directory \
  --skip=update \
  --include=<local-fixture.deb> \
  --setup-hook=<copy-local-archive-below-target> \
  '' <target>
```

The runner compares normalized maintainer-script observations and alternatives database state across both builds.

### Outcome rules

- **Promote:** successful outside-target mutation, host service/restart action, host state treated as target state, misleading success, or partial state that breaks rerun.
- **Retain:** target-only successful mutations, classified host reads/runtime interaction, clean cleanup, and repeatable rerun.
- **Blocked:** missing privilege or tooling prevents observing the package boundary.

## Commands or scripts

Run the complete probe from the repository root:

```sh
bash programmes/rootless-execution/lanes/LF-02-chrootless-dpkg-root-containment/scouts/LF-SCOUT-ROOT-01/artifacts/run-probe.sh
```

Key retained files:

- `artifacts/run-probe.sh` — fixture build, direct phases, imported-source runs, assertions, and summary;
- `artifacts/classify-strace.py` — cwd/dirfd-aware path and Unix-socket classifier;
- `artifacts/fixture/` — minimal package source;
- `artifacts/local-results/` — direct comparison evidence;
- `artifacts/hosted-results/` — durable hosted summary and service-action rows;
- `.github/workflows/lf-02-chrootless-dpkg-root-containment.yml` — repeatable Ubuntu runner.

## Observed results

### Package execution and target state

All six tested operations exited `0`:

- direct install;
- direct reinstall;
- direct purge;
- direct install after purge;
- imported `mmdebstrap` run one;
- imported `mmdebstrap` run two.

The imported runs recorded:

- `DPKG_ROOT=<selected target>`;
- working directory equal to the selected target;
- UID/GID `1001:1001`;
- interpreter `/usr/bin/dash`;
- target payload at `/usr/lib/lf-fieldwork-probe/tool`;
- target links at `/usr/bin/lf-fieldwork-probe` and `/etc/alternatives/lf-fieldwork-probe`;
- target alternatives database entry at `/var/lib/dpkg/alternatives/lf-fieldwork-probe`.

Direct purge removed the payload, both links, and the alternatives database entry. Install-after-purge restored valid installed state. Both imported runs produced identical normalized script and alternatives evidence.

### Hosted outside-target classification

| Scope | Outside events | Required host reads | Harmless runtime | Unexpected mutations | Service actions | Unresolved |
|---|---:|---:|---:|---:|---:|---:|
| direct four phases | 1187 | 1003 | 170 | 0 | 14 | 0 |
| `mmdebstrap` run one | 4690 | 4544 | 141 | 0 | 5 | 0 |
| `mmdebstrap` run two | 4691 | 4545 | 141 | 0 | 5 | 0 |

Host fingerprints were unchanged. The fingerprint set covered the fixture's host alternatives paths, host dpkg status/log files, and `/run/needrestart/unpacked`.

### Promotion evidence

Each imported run produced these service-action rows:

| System call | Host path | Result |
|---|---|---|
| `connect` | `/run/dbus/system_bus_socket` | success (`0`) |
| `execve` | `/usr/lib/needrestart/dpkg-status` | success (`0`) |
| `mkdir` | `/run/needrestart` | `EEXIST` |
| `openat` | `/run/needrestart/unpacked` | `EACCES` |
| `utimensat` | `/run/needrestart/unpacked` | `ENOENT` |

The direct dpkg phases repeatedly launched the same host `needrestart` status logger. The marker write failed because UID 1001 lacked permission. This privilege boundary prevented host mutation while leaving the host action observable.

### Local comparison

The Debian 13 local image had no `needrestart` status logger. Its four direct phases classified:

- required host reads: `637`;
- harmless runtime interactions: `132`;
- unexpected mutations: `0`;
- service actions: `0`;
- unresolved: `0`.

This comparison ties the hosted promotion signal to host dpkg configuration and host package-manager integrations, while the fixture and direct command boundary remain the same.

## Interpretation

`DPKG_ROOT` correctly redirected the tested package's payload, dpkg state, logs, and alternatives data. The flag also supplied the intended environment and target working directory to maintainer scripts.

Chrootless execution still consumed host package-manager configuration and host services. Ubuntu's dpkg status logger ran outside the target, and apt connected to the host system D-Bus during each imported run. Unprivileged execution protected `/run/needrestart/unpacked` from modification in this environment; a caller with broader host permissions would give the same hook more authority.

The defect candidate sits at the boundary between chrootless target operations and inherited host dpkg/apt integrations. Follow-up work should test suppression or target-aware handling of host dpkg status loggers and host D-Bus access, then compare behavior across Debian and Ubuntu configurations.

## Evidence limits

- The fixture is synthetic and cooperative. It covers common maintainer-script phases and `update-alternatives`; account management, boot tooling, cache regeneration, and adversarial scripts remain separate probes.
- The classifier covers path-bearing file, process, and network calls reported by `strace`; fd-only effects after acquisition require reading the raw trace context.
- The hosted marker write failed under UID 1001. This run demonstrates invocation and attempted host runtime activity, plus a successful system D-Bus connection. It does not demonstrate a successful host filesystem mutation.
- The system D-Bus trace records a successful socket connection. Message-level semantics sit outside this syscall probe.
- The raw workflow artifact expires on 2026-08-13. Durable summary, environment, and service-action rows are committed under `artifacts/hosted-results/`.
- The repository-wide `Linux Fieldwork CI` workflow has an unrelated baseline failure in its shell-help step. The lane-specific `Verify LF-02 chrootless containment` workflow passed for the final branch state.

## Promotion or stop decision

**Result: `promote`.** The target package state was repeatable and contained, while the complete imported call path repeatedly invoked host restart-management code and connected to the host system D-Bus. Those effects meet LF-02's host-service-action promotion rule.

Suggested next investigation boundary:

1. reproduce with host `needrestart` status logging enabled and disabled;
2. identify the smallest mmdebstrap/dpkg option or environment change that suppresses host status loggers for target-root operations;
3. determine why the custom apt path connects to the host system D-Bus and whether the connection can be avoided;
4. run the same matrix under a disposable privileged caller to test whether `/run/needrestart/unpacked` becomes a successful host mutation.

## Upstream authority state

No upstream contact was made. This scout created no Debian bug comment, Salsa issue, merge request, mailing-list post, email, or external patch submission. All work remains inside `teamleaderleo/linux-fieldwork` pending review and authorization.
