# Research Lanes

## In simple words

This is the short working index for choosing active Linux Fieldwork lanes. The full historical inventory remains in [`programmes/registry.yml`](programmes/registry.yml), and the dated portfolio view is [`CURRENT.md`](CURRENT.md).

Owner direction on `2026-08-03`: Debian and mmdebstrap work is parked. Open Debian carriers remain evidence, not an active task queue. Start new work from the non-Debian lanes below unless the owner explicitly reopens one exact Debian unit.

## Immediate active lanes

1. **Foundational systems event ownership** — [issue #419](https://github.com/teamleaderleo/linux-fieldwork/issues/419) / [PR #420](https://github.com/teamleaderleo/linux-fieldwork/pull/420)  
   curl multi-socket readiness re-arm, systemd namespace and VT ownership, and BuildKit context/cancellation boundaries.

2. **systemd-oomd reporter ownership** — [PR #245](https://github.com/teamleaderleo/linux-fieldwork/pull/245)  
   Reproduced policy collision with source-precedence, snapshot-lifecycle, atomicity, and typed-reducer candidates under validation.

3. **kmod recursive configuration identity** — [PR #412](https://github.com/teamleaderleo/linux-fieldwork/pull/412)  
   Move the deterministic whitespace/argv-loss reproduction from package behavior into exact current upstream-native tests.

4. **fsck and udev block-device coordination** — [PR #413](https://github.com/teamleaderleo/linux-fieldwork/pull/413)  
   Passing lock-domain control established independent locks; next probe owns the real ext4/udev lifecycle.

5. **jq and systemd source matrices** — [PR #414](https://github.com/teamleaderleo/linux-fieldwork/pull/414)  
   Interpret exact jq `path()` ordering and systemd bind-path compatibility results; retain WGPU retirement and UV hold.

6. **BuildKit go-archive implied-parent compatibility** — [PR #416](https://github.com/teamleaderleo/linux-fieldwork/pull/416)  
   Compare exact released dependency states and repaired current main before any integration claim.

7. **util-linux cpuset parse ownership** — retained packet [PR #404](https://github.com/teamleaderleo/linux-fieldwork/pull/404)  
   Keep the demonstrated double-free repair and native regression as upstream-system evidence; stop the Debian stable-update composition lane.

8. **DuckDB persisted wrong-result evidence** — [PR #334](https://github.com/teamleaderleo/linux-fieldwork/pull/334)  
   High-consequence secondary ART false-negative record awaiting eligible independent review.

9. **Repository execution and evidence integrity** — [PR #418](https://github.com/teamleaderleo/linux-fieldwork/pull/418) and [PR #328](https://github.com/teamleaderleo/linux-fieldwork/pull/328)  
   Relative-executable/cwd inventory coverage and fenced-example parser repair.

## Secondary bounded lanes

- [AAVMF and QEMU GIC matrix — PR #247](https://github.com/teamleaderleo/linux-fieldwork/pull/247)
- [Fork-enabled execution selection record — PR #257](https://github.com/teamleaderleo/linux-fieldwork/pull/257)
- [Name-brand Linux candidate map — PR #235](https://github.com/teamleaderleo/linux-fieldwork/pull/235)
- [LF-23 — cancellation, subprocess, and file-descriptor cleanup](programmes/services-resources/lanes/LF-23-cancellation-subprocess-fd-cleanup/brief.md)
- [LF-20 — systemd stop, timeout, and descendant cleanup](programmes/services-resources/lanes/LF-20-systemd-stop-timeout-descendant-cleanup/brief.md)
- [LF-22 — cgroup v2 delegation and cleanup](programmes/services-resources/lanes/LF-22-cgroup-v2-delegation-cleanup/brief.md)
- [LF-14 — archive extraction and metadata contracts](programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/brief.md), only for project-independent archive behavior rather than another mmdebstrap packet.

## Parked lanes

The following programme lanes remain historically indexed but are not active selection surfaces:

- LF-02 chrootless `DPKG_ROOT` containment;
- LF-07 maintainer-script interruption and idempotency;
- LF-11 merged-`/usr` package assumptions;
- LF-12 reproducible Debian package variance;
- Debian/mmdebstrap packet, package-test, tarfilter, chrootless, and submission lanes under the old push issue #194.

Do not resume them from an open PR, queued workflow, old priority label, or unfinished checklist. Reopening requires an explicit owner instruction naming the exact unit.

## Programmes

- [`Ecosystem contributions and upstream fixes`](programmes/ecosystem-contributions/STATUS.md)
- [`Rootless execution, namespaces, and mounts`](programmes/rootless-execution/STATUS.md)
- [`Filesystems, archives, and disk images`](programmes/filesystems-images/STATUS.md)
- [`Services, processes, and resources`](programmes/services-resources/STATUS.md)
- [`Security and networking boundaries`](programmes/security-networking/STATUS.md)
- [`Boot, devices, and deeper kernel work`](programmes/boot-kernel/STATUS.md)
- [`Debian packages, transactions, and builds`](programmes/debian-packages/STATUS.md) — retained history, currently parked.

## Selection rule

Choose a lane whose bounded question and environment fit the available evidence path. Begin with source and test mapping, use adjacent-context discriminators that can make the current direction lose, and stop when the selected contexts cannot change the decision.

Preserve exact evidence and negative results. Do not treat this index, a programme entry, or an open carrier as authority to contact upstream.
