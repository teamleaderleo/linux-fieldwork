# LF-SCOUT-ROOT-01 — Chrootless `DPKG_ROOT` containment

## In simple words

A tiny package with four maintainer scripts was installed into a disposable target directory while its scripts executed through host programs. `dpkg` supplied the intended `DPKG_ROOT`, started the scripts with the target as their working directory, and the package's `update-alternatives` action created its database entry and links beneath that target. Four direct dpkg phases completed cleanly: install, reinstall, purge, and install after purge.

The local trace classified 769 accesses outside the target. They were host program, library, configuration, locale, and identity reads, plus device/process runtime interaction. It found zero successful host mutations, zero service actions, and zero unresolved accesses. Host dpkg and alternatives sentinels remained unchanged.

**Decision: `retain`.** Keep this bounded negative result and its reusable probe. This fixture gives no promotion signal for a defect investigation.

## Scout identity and home lane

- Scout-ID: `LF-SCOUT-ROOT-01`
- Home lane: `LF-02`
- Assignment: issue `#11`
- Working branch: `scout/lf-scout-root-01/lf-02-dpkg-root-containment`
- Reviewer: `LF-SCOUT-DEB-02`
- Cross-review duty: `LF-SCOUT-PROC-01` on LF-23 after its `READY FOR REVIEW` post

## Exact source or package boundary

### Imported source

- Project: Debian `mmdebstrap`
- Imported path: `upstream/mmdebstrap/`
- Requested revision: `debian/1.5.7-3`
- Resolved upstream commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Repository import commit: `51c8480d7e61b3e31d74f69864042a3fc8c1d772`
- Source metadata: `upstream/mmdebstrap/.linux-fieldwork-source.json`
- Imported executable version: `1.5.7`
- Imported executable blob used for source reading: `dfb5e37b68271a46b9e75128cdd85975fbb383a1`

The branch begins after the repository's separate explicit-`TMPDIR` candidate. That candidate does not alter the chrootless dpkg call path examined here.

### Package fixture

- Package: `lf-fieldwork-probe`
- Version: `1.0`
- Architecture: `all`
- Dependencies: none
- Local built archive size: `1180` bytes
- Local built archive SHA-256: `0f41eb83272ab38f9d24524da2568967a686d3cfc2b76bd9659df30eb2df74b2`
- Fixture source: `artifacts/fixture/`

The fixture contains one payload at `/usr/lib/lf-fieldwork-probe/tool` and four maintainer scripts:

- `preinst` records `DPKG_ROOT`, working directory, UID/GID, and interpreter;
- `postinst` records the same values and calls `update-alternatives --install`;
- `prerm` calls `update-alternatives --remove`;
- `postrm` records its phase.

This was the smallest useful fixture because it has no package dependencies or network requirement, exercises every common maintainer-script phase, and uses a common dpkg-root-aware helper with externally visible database and symlink effects.

## Environment and privileges

### Local bounded run

- Date: 2026-07-30
- Runner: disposable Debian 13 container
- Kernel: Linux `6.12.13`, x86_64
- Orchestration UID: `0`
- Package action UID/GID: `65534:65534` (`nobody`)
- `dpkg`: `1.22.22`
- `apt`: `3.0.3`
- `update-alternatives`: `1.22.22`
- Network access: unavailable
- Target: `/tmp/lf-02-work/target`

The package action ran without host privileges. Root was used only to prepare the disposable runner and then hand the package operation to UID 65534.

### GitHub-hosted reproducible run

The retained runner at `artifacts/run-probe.sh` executes under the ordinary GitHub-hosted runner account on Ubuntu 24.04. It runs direct dpkg phases and two full imported-`mmdebstrap` builds under `strace`, stores all generated evidence below `artifacts/results/`, and is invoked by `.github/workflows/lf-02-chrootless-dpkg-root-containment.yml`.

## Source and test map

The imported call path is:

1. `setup()` performs setup, apt update/download, and extraction.
2. `setup()` calls `run_essential()` before `run_install()`.
3. In chrootless mode, `run_essential()` invokes host `dpkg` directly with:
   - `--force-not-root`
   - `--force-script-chrootless`
   - `--root=<target>`
   - `--log=<target>/var/log/dpkg.log`
4. In chrootless mode, `run_install()` invokes host `apt-get` with dpkg options carrying the same flags and target.
5. `run_progress()` forks and directly `exec`s the requested host command; the chrootless branch supplies no chroot wrapper.
6. `dpkg --force-script-chrootless` executes maintainer scripts in the host process environment and exports `DPKG_ROOT` for package code and helpers.

Relevant imported source ranges in `upstream/mmdebstrap/mmdebstrap`:

- setup order and handoff: approximately lines `2978-2985`;
- apt configuration rooted at the target: approximately lines `3085-3112`;
- progress fork and direct exec: approximately lines `1847-1902`;
- direct essential dpkg command: approximately lines `3918-3963`;
- chrootless apt/dpkg options for remaining packages: approximately lines `4056-4065`;
- root-without-fakeroot safety check: approximately lines `6051-6064`;
- documented chrootless warning and host dependency boundary: approximately lines `8187-8201`.

The source also records a known host-input boundary: dpkg reads host configuration before command-line root options, so host `/etc/dpkg/dpkg.cfg*` can affect the target operation.

## Probe design and distinguishing outcomes

### Direct dpkg probe

The direct probe isolates the exact command boundary used by `run_essential()` and runs:

1. install;
2. reinstall over the installed package;
3. purge;
4. install after purge.

Each phase traces process execution and path-bearing filesystem/network system calls. Before and after the four phases, the probe fingerprints host package state and three sentinel paths.

### Imported mmdebstrap probe

The reusable runner calls the imported executable with:

- `--mode=chrootless`;
- `--variant=custom`;
- the local `.deb` as the only included package;
- `--skip=update` so the package path stays local and the result has no repository-network dependency;
- directory output;
- a setup hook that makes the local archive available at the same absolute path below the target, matching mmdebstrap's documented local-package requirement.

It repeats the full build into two fresh targets and compares normalized script and alternatives state.

### Distinguishing outcomes

- **Contained negative result:** target-only successful mutations, explicit host reads/runtime interaction, clean purge, and successful rerun.
- **Promotion signal:** any successful outside-target mutation, host service-control execution, host state interpreted as target state, misleading success, or partial target state that breaks a rerun.
- **Blocked result:** missing privilege/tool support prevents observing the package boundary.

## Commands or scripts

The local command boundary was:

```sh
env -i \
  PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/tmp/lf-02-work/target/nonexistent-home \
  TMPDIR=/tmp/lf-02-work/target/tmp \
  XDG_RUNTIME_DIR=/tmp/lf-02-work/target/run \
  LC_ALL=C \
  dpkg \
    --force-not-root \
    --force-script-chrootless \
    --root=/tmp/lf-02-work/target \
    --log=/tmp/lf-02-work/target/var/log/dpkg.log \
    --install /tmp/lf-02-work/lf-fieldwork-probe_1.0_all.deb
```

The purge phase replaced the final argument with:

```sh
--purge lf-fieldwork-probe
```

Run the complete retained probe from the repository root with:

```sh
bash programmes/rootless-execution/lanes/LF-02-chrootless-dpkg-root-containment/scouts/LF-SCOUT-ROOT-01/artifacts/run-probe.sh
```

The runner:

- builds the fixture with `dpkg-deb --build --root-owner-group`;
- records exact versions and source identity;
- traces all dpkg/mmdebstrap child processes with `strace -ff`;
- classifies each outside-target event with `artifacts/classify-strace.py`;
- compares host fingerprints;
- verifies target payload, dpkg state, alternatives state, cleanup, and reruns;
- stores raw traces, commands, logs, trees, classifications, and summary JSON in `artifacts/results/`.

## Observed results

### Script execution boundary

The local trace showed:

- target maintainer-script paths under `/tmp/lf-02-work/target/var/lib/dpkg/`;
- host `/usr/bin/dash` selected by each script's shebang;
- host `mkdir`, `id`, `readlink`, and `update-alternatives` processes;
- `DPKG_ROOT=/tmp/lf-02-work/target` inside scripts;
- script working directory `/tmp/lf-02-work/target`;
- UID/GID `65534:65534` inside scripts.

### Successful target mutations

Observed writes beneath the target included:

- package payload;
- target dpkg status/info/triggers state;
- target dpkg and alternatives logs;
- `/var/lib/dpkg/alternatives/lf-fieldwork-probe` beneath the target;
- `/etc/alternatives/lf-fieldwork-probe` beneath the target;
- `/usr/bin/lf-fieldwork-probe` beneath the target;
- the fixture's script observation log.

The alternatives links used absolute logical targets, as dpkg alternatives normally does, while the link objects and database entry were created beneath `DPKG_ROOT`.

### Outside-target classification

Across install, reinstall, purge, and install after purge:

| Category | Events |
|---|---:|
| required host read | 637 |
| harmless runtime interaction | 132 |
| unexpected mutation | 0 |
| service action | 0 |
| unresolved | 0 |
| **total** | **769** |

Required host reads covered:

- executable and dynamic-library lookup;
- host dpkg configuration;
- locale and identity files;
- metadata reads and target ancestor traversal;
- the local package archive used as probe input.

Harmless runtime interaction covered:

- `/dev/null`;
- `/proc` and `/sys` runtime reads;
- failed nscd Unix-socket probes;
- failed `mkdir` calls returning `EEXIST` while traversing existing `/tmp` ancestors.

### Host integrity checks

These host sentinel paths were absent before and after:

- `/usr/bin/lf-fieldwork-probe`;
- `/etc/alternatives/lf-fieldwork-probe`;
- `/var/lib/dpkg/alternatives/lf-fieldwork-probe`.

Hashes for these host files remained unchanged:

- `/var/lib/dpkg/status`;
- `/var/log/dpkg.log`;
- `/var/log/alternatives.log`.

### Cleanup and rerun

- Initial install: exit `0`.
- Reinstall: exit `0`.
- Purge: exit `0`.
- Install after purge: exit `0`.
- Purge removed the payload, both alternatives links, and alternatives database entry from the target.
- The fixture deliberately retained its target-side observation directory and log.
- dpkg emitted its normal warning that `/usr` remained nonempty and therefore stayed present.
- The clean install after purge produced valid installed state again.

Retained local summaries are under `artifacts/local-results/`.

## Interpretation

For this deliberately small package, `DPKG_ROOT` containment held across dpkg database work, payload extraction, all four maintainer-script phases, and `update-alternatives` state changes. Maintainer scripts still had the power to execute host programs and read host state. The observed package respected the target root when constructing every mutable path.

The most important boundary is therefore package cooperation. `--force-script-chrootless` relocates dpkg's own work and supplies `DPKG_ROOT`; it does not confine arbitrary script syscalls. A package that opens `/etc/...`, calls a host service manager, or ignores `DPKG_ROOT` can still cross the host boundary. This fixture exercised a compliant helper and produced a contained negative result.

The host dpkg configuration read is expected from the imported source and remains a reproducibility/input concern. The selected host configuration introduced no outside mutation in this run.

## Evidence limits

- The fixture is synthetic and intentionally cooperative. It exercises a common helper, while account management, init-system integration, cache regeneration, boot tooling, absolute-path shell redirection, and adversarial scripts remain outside this probe.
- The local run traced direct dpkg rather than the complete imported mmdebstrap orchestration because the local container lacked network access and packaged `strace`. The retained GitHub runner covers the complete imported path with local package input.
- The local custom ptrace tracer captured process execution plus a bounded set of path-bearing syscalls. It cannot attribute every fd-only operation after an open, every kernel-internal path traversal, or syscall families outside its capture list.
- The `strace` classifier resolves ordinary absolute paths precisely. Relative paths tied to changing working directories or directory file descriptors receive conservative treatment and remain visible in the raw trace.
- Host integrity fingerprints cover package database/log files and fixture-specific alternatives sentinels. The syscall trace supplies the wider path inventory.
- A contained result for this package provides no universal safety claim for chrootless package installation.

## Promotion or stop decision

**Result: `retain`.** Retain the negative result, fixture, classifier, and repeatable CI probe. The observed effects stayed within the declared target, required host reads were classified, purge completed, and reruns succeeded. No candidate defect or broader investigation is promoted from this package boundary.

A future lane extension should select a real package with account, cache, service, or boot-related maintainer-script behavior and apply the same classifier.

## Upstream authority state

No upstream contact is authorized or performed. This scout created no Debian bug comment, Salsa issue, merge request, mailing-list post, email, or external patch submission. All work remains inside `teamleaderleo/linux-fieldwork`.
