# mmdebstrap and autopkgtest handoff — 2026-07-30

## Purpose

This note reconciles the mmdebstrap work after a rapid sequence of historical recovery, current-sid reproduction, harness repair, and adjacent source investigations. It is a pickup map, not a new ownership claim.

Coordination issue: #181.

## Canonical historical answer

The historical Debian failure is resolved. Issue #53 is closed and is the canonical tracker.

Debian CI run `72574145` failed in the `mmdebstrap` **test fixture**, not the mmdebstrap runtime:

- package: `mmdebstrap 1.5.7-3`;
- trigger: `migration-reference%2F0`;
- testbed: Debian testing amd64;
- first and only failed case: `(252/283) dev-ptmx --mode=root --variant=apt`;
- passed: `158`;
- skipped: `93`;
- testbed `bsdutils`: `1:2.42.2-1`.

`tests/dev-ptmx` created an apt-variant root with:

```text
--include=gcc,libc6-dev,python3,passwd
```

and later executed `script(1)` inside that root. The first unavailable command was:

```text
chroot: failed to run command ‘script’: No such file or directory
```

`/usr/bin/script` is provided by `bsdutils`. The test had relied on `bsdutils` being Essential; the util-linux 2.42 packaging transition exposed that undeclared dependency.

Durable records already on `main`:

- `investigations/mmdebstrap-dev-ptmx-bsdutils/README.md`;
- `investigations/mmdebstrap-dev-ptmx-bsdutils/debci-72574145-summary.json`;
- `investigations/mmdebstrap-dev-ptmx-bsdutils/0001-include-bsdutils.patch`;
- `tests/test_mmdebstrap_dev_ptmx_dependency.py`;
- `notes/debian/tests-must-declare-command-providers-not-essential-set-assumptions.md`.

Focused ownership: issue #84. Historical artifact carrier: closed PR #82. The candidate carrier PR #86 was closed after the durable files were retained elsewhere.

## Work completed during the reduction phase

The initial work established a central tracker, separated Debian and Ubuntu behavior, extracted reusable execution tooling, and recorded several independent defects.

### Merged or retained outcomes

- PR #64 merged the neutral `77` classification for unsupported non-Debian archive identities.
- PR #90 merged local mirror HTTP-server readiness, retained startup diagnostics, and child cleanup.
- The historical `dev-ptmx`/`bsdutils` result and regression are retained on `main`.
- PR #158 merged the first scheduling correction for `root-without-cap-sys-admin`, removing the incompatible globally injected mount hook from that execution path.

### Still-active outcomes

- Issue #54 / PR #72: reusable BTS capture and current-sid reproduction tooling. Issue #54 remains open until the reusable ownership model is merged or otherwise resolved.
- Issue #75: same-repository guard before privileged mmdebstrap PR execution. The guard exists in PR #72 but is not canonical on `main` while that PR remains open.
- Issue #80 / PR #92: exact field-1 matching for `/etc/subuid` and `/etc/subgid`; exact-head CI is green and the PR remains open.
- Issue #79 is completed by merged PR #90.
- Issue #153 / merged PR #158: hook-free scheduling for the no-`CAP_SYS_ADMIN` case.
- PR #171: follow-up that preserves hard-failure semantics for the hook-free capability case; merged PR #158 alone routes it into a phase that converts failures to neutral `77`.
- Issue #155: the mirror-cache rerun uses `curl` without declaring it.
- PR #161: current carrier for the reusable observer/trigger/selected-universe/owner note and log classifier.

## PR #72 reduction history

PR #72 is useful execution history but contains stale historical interpretation. Use #53 and the retained `dev-ptmx` record for historical ownership.

The branch exposed and corrected several harness failures before reaching named package-test cases:

1. repository shell files created with mode `0644` were executed directly, producing status `126`;
2. the container omitted required `patch`, producing an early neutral result;
3. the inherited wrapper patch had malformed hunk counts;
4. the first wrapper design failed the package POD gate;
5. current sid then reached `(30/284) create-directory` and exposed a Deb822 `sourcesfilter` incompatibility;
6. after the Deb822 candidate, the next first failure was `(41/284) root-without-cap-sys-admin`, where the injected file-mirror hook attempted a bind mount after the case deliberately dropped `CAP_SYS_ADMIN`.

These are current-sid compatibility and observability findings. They are separate from historical run `72574145`.

## Stale and superseded context

Contributors should avoid restarting from these older statements:

- PR #9 is the original broad investigation carrier. Its chronology and artifact references are useful, but its unresolved-owner language is obsolete.
- PR #72 still says the Deb822 incompatibility is the strongest historical owner hypothesis. That paragraph is obsolete; #53 contains the recovered historical answer.
- PR #60 is closed and superseded by PR #161 for the reusable classifier/note.
- Early util-linux namespace, mount, glibc, systemd, and archive-mismatch hypotheses were reasonable before the historical log was recovered. They are not the owner of run `72574145`.

Issue #182 tracks cleanup of stale carriers after this handoff lands.

## What other active work is doing

The repository has moved beyond one bug into several focused mmdebstrap and Linux reliability streams.

### Package-test and hook boundaries

- PR #171 preserves hard failure for the hook-free capability case.
- PR #179 contains `file-mirror-automount` setup and cleanup targets against traversal and symlink escape.
- PR #92 fixes exact subordinate-ID account matching.
- Issue #155 tracks an undeclared `curl` dependency in a mirror-cache rerun.

### Process status and cancellation

- PR #138 preserves `gpgv` verifier exit status.
- PR #177 validates `--status-fd` option forms.
- PR #180 stacks signal forwarding and child reaping on PR #138.
- PR #143 prevents parent-only SIGINT from falling through to package-test success.
- PR #159 makes `make_mirror.sh` terminate after signal cleanup.
- PR #166 preserves proxysolver child signal termination.
- PR #172 makes the QEMU image builder exit after signal cleanup.

These carriers overlap in process-lifecycle concepts and sometimes stack on one another. Issue #183 tracks overlap and canonical stacking order.

### Cache-proxy integration

- PR #162 is the canonical composition gate for atomic publication, downstream framing, and declared-length validation.
- PR #147 handles failures after downstream response commitment.
- PR #169 rejects non-200 origin responses under normal and optimized Python.
- merged PRs #137 and #139 retain declared-length validation and request-header separation.

### Other active programmes

- PR #151 handles GNU tar basic versus extended transform regex dialects.
- PR #178 extends LF-02 into upgrade, failed configure, recovery, and purge state.
- PR #142 refreshes ecosystem overlap and avoids duplicating an active external fix.

## Recommended pickup order

1. Treat #53 and `investigations/mmdebstrap-dev-ptmx-bsdutils/` as the canonical historical record.
2. Review PR #171 before treating merged PR #158 as complete, because failure classification matters as much as hook removal.
3. Decide the ownership/disposition of PR #72 and close issue #54 only after reusable tooling is on `main` or the workflow is moved back out of `main`.
4. Merge or otherwise disposition PR #92, then keep subid range allocation policy outside that exact-match fix.
5. Resolve stale carrier cleanup under #182.
6. Map overlap under #183 before opening more broad mmdebstrap process or hook audits.
7. Keep cache-proxy integration on the canonical composition carrier rather than stacking isolated green patches without a shared source gate.

## My contribution boundary

The work I initiated or materially advanced in this phase included:

- central coordination issue #53;
- tooling ownership issue #54;
- non-Debian classification issue #55 and merged PR #64;
- privileged fork-PR boundary issue #75;
- HTTP readiness issue #79 and the investigation that became merged PR #90;
- exact subid account matching issue #80 and PR #92;
- the first durable transition classifier/dossier carrier, later superseded by PR #161;
- PR #72 tooling extraction and its execution-discovered harness corrections;
- issue #181 for this handoff, #182 for stale carriers, and #183 for active-queue overlap.

Later contributors recovered the historical log, identified the exact `dev-ptmx` fixture owner, retained the focused candidate on `main`, and expanded the current-sid and reliability work substantially.

## Authority

This is an internal Linux Fieldwork handoff. No Debian, Ubuntu, or other external issue, email, merge request, patch submission, comment, or review is authorized by this note.
