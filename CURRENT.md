# Linux Fieldwork — current direction

Observed: `2026-08-03 14:58 +08:00`  
Base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`

## In simple words

Linux Fieldwork contains valuable systems research, but its open list is dominated by historical Debian and mmdebstrap carriers. The repository owner no longer wants Debian work to consume active attention.

The active direction is now non-Debian Linux and upstream systems work: process and event ownership, service policy, build graphs, filesystem and device coordination, command argument identity, archive contracts, wrong-result persistence, and reusable repository integrity.

This is a dated routing snapshot. It does not erase branches or evidence and grants no external-contact authority.

## Active foreground

### Foundational systems deep dive

- parent issue [#419](https://github.com/teamleaderleo/linux-fieldwork/issues/419);
- research carrier [#420](https://github.com/teamleaderleo/linux-fieldwork/pull/420);
- targets: systemd, BuildKit, and curl;
- strongest current result: a curl/Ceph-style split-response hang is reproduced when a one-shot Asio readiness wait is not re-armed while curl's requested input interest remains unchanged; a generation-safe re-arm control completes;
- next bounded probes: systemd vmspawn user-namespace bind handling, BuildKit context laziness, BuildKit rootless cancellation, and systemd VT event ordering.

### systemd-oomd reporter ownership

- carrier [#245](https://github.com/teamleaderleo/linux-fieldwork/pull/245);
- current systemd VM behavior is reproduced: a later user-manager `auto` contribution removes an earlier system-manager pressure policy for the same cgroup path;
- source-precedence product slice, connection-generation lifecycle model, snapshot atomicity controls, and a typed C reducer are under validation.

### kmod recursive configuration identity

- carrier [#412](https://github.com/teamleaderleo/linux-fieldwork/pull/412);
- package-level deterministic reproduction shows a nested `modprobe` loses a requested configuration path containing whitespace because `MODPROBE_OPTIONS` does not preserve argument boundaries;
- next transition: build exact current kmod source and add the discriminator to its native fake-root/fake-syscall test suite.

### fsck and udev lock identity

- carrier [#413](https://github.com/teamleaderleo/linux-fieldwork/pull/413);
- privileged probe passed and established that current `fsck -l` and udev's whole-device BSD flock occupy independent lock objects;
- next transition: synchronized disposable real-ext4/udev fixture for the actual UUID/database lifecycle.

### jq, systemd, UV, and WGPU cross-ecosystem round

- carrier [#414](https://github.com/teamleaderleo/linux-fieldwork/pull/414);
- jq destructuring inside `path()` has a controlled source-order, Valgrind, and complete-suite matrix;
- systemd bind-path whitespace is overlap review only because an active public implementation owns the source direction;
- WGPU/Naga bitcast work is retired after current source accepted every controlled case;
- the UV lockfile diagnostic is held after complete review found a valid requirements-file false positive.

### BuildKit go-archive compatibility

- carrier [#416](https://github.com/teamleaderleo/linux-fieldwork/pull/416);
- matrix compares v0.2.0, v0.2.1, v0.3.0, and repaired current go-archive main for directory entries whose parent is implied;
- use the exact terminal matrix result before making any BuildKit integration claim.

### util-linux cpuset parse ownership

- historical packet [#404](https://github.com/teamleaderleo/linux-fieldwork/pull/404);
- installed util-linux 2.41-5 reproducibly aborts in text and JSON modes on malformed CPU-online input because the output cpuset can be freed twice;
- canonical source repair applies cleanly, the exact actual-binary baseline/candidate matrix passed, and controlled fork head `95ebc67e521195741040ffebb58756b259fb69b2` passed the focused native regression;
- Debian stable-update composition is cancelled; retain the upstream util-linux source result independently and require fresh current-source review before any future proposal.

### DuckDB secondary ART persisted wrong result

- carrier [#334](https://github.com/teamleaderleo/linux-fieldwork/pull/334);
- official release-artifact matrix retains a high-consequence false-negative index-scan result while sequential reads retain the row;
- the exact one-file evidence restack passed repository CI and needs eligible independent review before promotion.

### Reusable repository integrity

- [#418](https://github.com/teamleaderleo/linux-fieldwork/pull/418) — source-change coverage for the relative-executable/cwd inventory plus read-only/untrusted-input hardening;
- [#328](https://github.com/teamleaderleo/linux-fieldwork/pull/328) — executed repair for fenced-example parsing in carrier-state audit, technically review-ready.

### Additional bounded lanes

- [#247](https://github.com/teamleaderleo/linux-fieldwork/pull/247) — AAVMF boot across QEMU GIC modes under TCG;
- [#257](https://github.com/teamleaderleo/linux-fieldwork/pull/257) — retained fork-enabled execution selection and source review;
- [#235](https://github.com/teamleaderleo/linux-fieldwork/pull/235) — name-brand actionable Linux candidate map, useful as historical selection input rather than the current queue.

## Debian and mmdebstrap state

Owner direction on `2026-08-03`: **park Debian and mmdebstrap work**.

Do not begin or continue:

- Debian package-composition or stable-update work;
- mmdebstrap package matrices, tarfilter packets, chrootless harness expansion, Salsa refresh, or submission preparation;
- new Debian-specific research lanes merely because a carrier remains open;
- further work under the old last-mile push issue #194.

Preserve:

- exact source and package identities;
- workflow, artifact, and review receipts;
- branches and pull-request discussions;
- negative results and reusable technical lessons;
- explicit reopening triggers.

Close or mark not planned:

- execution-only carriers whose result has transferred;
- Debian/mmdebstrap-only research or packet PRs with no active non-Debian successor;
- stale stacks whose unique evidence is already retained elsewhere.

A project is not retired merely because Debian was used as a control environment. Current upstream work on systemd, util-linux, BuildKit, curl, kmod, jq, DuckDB, Nixpkgs, archive libraries, and repository tooling may continue when its question is independently useful and no longer depends on completing a Debian packaging lane.

## Historical Debian surfaces

The following families should leave active owner routing while remaining preserved:

- mmdebstrap packet and tarfilter units, including PRs #399, #400, #402, #405, #408, #410, and #415, closed without merge on 2026-08-03;
- chrootless package and directory-mtime execution/evidence stacks, including #361, #366, #381, #383, #388, #389, #390, #391, #394, #395, and #396;
- older LF-02 chrootless host-integration stacks, including #21, #22, #99, and #104;
- tarfilter dependency and harness repair stacks, including #248, #289, #301, and #310;
- the old broad last-mile push [#194](https://github.com/teamleaderleo/linux-fieldwork/issues/194), closed `not planned`.

This list is routing guidance, not evidence deletion. A branch may remain open temporarily while its closing note or successor map is synchronized.

## Immediate operating order

1. Complete and classify the curl/Asio re-arm discriminator under #419/#420.
2. Settle exact direct-head systemd-oomd prototype and reducer results under #245.
3. Move the kmod whitespace reproduction into exact upstream-native tests.
4. Build the real ext4/udev lifecycle discriminator after the passing lock-domain control.
5. Interpret the jq/systemd and go-archive matrices at their exact heads.
6. Preserve the util-linux source result outside its retired Debian package wrapper.
7. Obtain independent review for the DuckDB ART wrong-result record and the carrier-state parser repair.
8. Close or park remaining Debian/mmdebstrap-only carriers without running new package work.
9. Keep all upstream contact separately unauthorized unless the owner grants exact authority for one interaction.

## Reopening rule

Debian or mmdebstrap work re-enters only after an explicit owner instruction naming the exact unit or question. A queued workflow, old priority label, open pull request, unfinished checklist, or available runner does not override this direction.
