# systemd Target Map

## In simple words

`systemd` coordinates services, sessions, devices, namespaces, credentials, virtual machines, and shutdown on Linux systems. It recurs in Linux Fieldwork because small mistakes at these boundaries can leave a process running with the wrong authority, abandon an in-progress transition, or clean up the wrong resources.

## Source identity

- Canonical repository: `https://github.com/systemd/systemd.git`
- Canonical branch: `main`
- Current research revision: `ac33190d1f66e870d511827cbed3ebeee2d704c2`
- Controlled fork: `https://github.com/teamleaderleo/systemd.git`
- Fork default branch observed: `main`
- Fork head observed before this round: `6a863b4dc31adc49fdfdd5deba32ed1b115adda3`
- Current-main relation at observation: canonical `main` was 18 commits ahead and the fork had no unique commits relative to that merge base.
- Imported source tree: not yet present under `upstream/`; repository reads in this round are pinned to the canonical commit above.

Do not rewrite the fork default branch for research. Use a separate exact-base branch when execution begins.

## Why it recurs

The project crosses Linux capabilities, user and mount namespaces, cgroups, process supervision, device events, D-Bus, Varlink, virtual-machine launch, login sessions, filesystems, and kernel-facing state machines.

## Relevant programmes

- [`Rootless execution, namespaces, and mounts`](../../programmes/rootless-execution/STATUS.md)
- [`Services, processes, and resources`](../../programmes/services-resources/STATUS.md)
- [`Security and networking boundaries`](../../programmes/security-networking/STATUS.md)
- [`Boot, devices, and deeper kernel work`](../../programmes/boot-kernel/STATUS.md)

## Mapped lanes

- LF-03 — rootless ownership and idmapped mounts
- LF-06 — namespace capability lifecycle
- LF-20 — systemd stop, timeout, and descendant cleanup
- LF-22 — cgroup v2 delegation and resource cleanup
- LF-23 — cancellation, subprocess, and file-descriptor cleanup
- LF-26 — capability and credential transitions
- LF-31 — udev and device hotplug races

## Current investigations

- [`systemd-vmspawn` unmapped bind and user-namespace entry](../../investigations/systemd-vmspawn-unmapped-bind-userns/README.md)

## Secondary research queue

- `systemd/systemd#42091` — logind VT-release race between signalfd and D-Bus dispatch. Keep this separate from vmspawn: it is an event-order and explicit-state question, not a namespace-entry fix.
- VM test harness archaeology under `test/units/TEST-87-AUX-UTILS-VM.*`.
- Credential and capability behavior around helper processes after namespace entry.

## Source and test surfaces

Start with:

- `src/vmspawn/vmspawn.c`
- `src/basic/namespace-util.c`
- `src/vmspawn/vmspawn-mount.c`
- `test/units/TEST-87-AUX-UTILS-VM.vmspawn.sh`
- `test/units/TEST-87-AUX-UTILS-VM.bind-volume.sh`
- nearby namespace utility tests

For login races, keep separate source and evidence around `src/login/`, `sd-event` priorities, signalfd handling, D-Bus request dispatch, and kernel VT ioctls.

## Policy boundary

This map authorizes reading and controlled-fork research only. No upstream issue, pull request, comment, email, review, or other systemd interaction is authorized.