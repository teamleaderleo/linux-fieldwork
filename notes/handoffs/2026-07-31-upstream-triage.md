# Upstream triage and severity map for the current mmdebstrap findings

Recorded: 2026-07-31 00:01 +08:00 / 2026-07-30 16:01 UTC

Companion operational handoff: `notes/handoffs/2026-07-30-active-mmdebstrap-work.md`

## Authority

This note is internal coordination only. It does not authorize or perform any Debian BTS update, upstream issue, email, merge request, patch submission, comment, or review.

No external contact was made while preparing this triage.

## Executive decision

Stop discovery for the current sprint. Use the remaining capacity to:

1. separate local regressions from upstream defects;
2. identify one canonical owner for each finding;
3. finish exact-current-head and composition gates;
4. close duplicate or diagnostic carriers;
5. prepare small upstream-ready units without sending them;
6. start another discovery pass only after this queue is reduced.

The findings do not currently establish a 9/10 or 10/10 remote, unauthenticated, system-wide compromise. Several are serious, narrow 6/10 to 7/10 correctness, trust, or containment defects. Many others are 2/10 to 5/10 test, compatibility, or lifecycle defects.

The numbers below are prioritization aids, not CVSS scores.

## Explain it like I am five

`mmdebstrap --mode=chrootless` builds a pretend Linux root directory, but package setup scripts still run as real programs on the host.

- Environment finding: the program can hand those scripts too much from the caller's backpack, including credential or session information.
- Temporary-directory finding: while emptying that backpack in our local hardening patch, we accidentally removed the note telling scripts to put scratch files inside the pretend root. They then used the host's shared `/tmp`. We restored the note.
- PATH finding: a package script can look in the caller's personal tools drawer before the package manager's tools drawer.
- Tarfilter findings: some visible labels on archive boxes are changed while hidden labels, link arrows, or sparse-file instructions can remain stale.
- Caching-proxy findings: a small local delivery helper trusts address and response information too much, and can publish a package before delivery is complete.
- Verifier-wrapper finding: the seal checker can fail while the wrapper reports the output filter's success.

The chrootless boundary deserves respect, but it is not a sandbox. Package scripts already run as host processes with the invoking user's authority. Our findings are primarily defense in depth, deterministic behavior, archive integrity, cache integrity, and trustworthy failure reporting.

## The small temporary-directory issue is separate

### Exact classification

Issue #69 and merged PR #74 are the small `TMPDIR` item.

Merged PR #57 introduced a clean chrootless maintainer-script environment. Its first allowlist removed the caller's `TMPDIR` but did not restore the target-derived value. Ordinary temporary helpers such as `mktemp` therefore fell back to host `/tmp`.

PR #74 corrected that local regression by:

- deriving `TMPDIR` as `<target>/tmp`;
- creating the directory as mode `01777` when absent;
- refusing a symlink or non-directory at that path;
- using the same value for direct and apt-managed chrootless dpkg paths;
- refusing to inherit an arbitrary caller `TMPDIR`.

### Upstream conclusion

This is not a standalone defect in current upstream `mmdebstrap`. Current upstream already creates the target `/tmp` and assigns target-derived `TMPDIR` for chrootless operation. The regression was introduced by our local environment-scrubbing candidate.

Therefore:

- keep PR #74 as a distinct compatibility prerequisite and regression in the local hardening series;
- do not file a separate upstream issue claiming that current upstream sends chrootless temporary files to host `/tmp`;
- if the broader environment hardening is proposed upstream, include or precede it with the target-derived `TMPDIR` guarantee;
- do not combine the `TMPDIR` correction with the broader `PATH` policy discussion.

Estimated severity: **3/10 to 4/10**, medium correctness/containment in the local mitigation candidate. It is not a sandbox escape or privilege escalation.

## Chrootless findings

### Caller environment and credentials

Canonical local owner: merged PR #57 / issue #40.

Current upstream behavior passes a broad caller environment into host-executing package-management paths. The local hardening candidate refuses credential-like variables and uses an explicit maintainer-script environment while retaining required package-management state.

Estimated severity: **6/10** defense-in-depth and credential/session exposure boundary.

Why not higher:

- package scripts are already host-executing code;
- this does not establish a new privilege boundary or sandbox escape;
- impact depends on caller environment and package behavior.

Upstream readiness: **architectural review required**. Do not send the merged local patch as an unqualified security fix. Reduce it to a documented environment contract, preserve `TMPDIR`, fakeroot, QEMU, locale, debconf, reproducibility, repository-authentication, and override behavior, and explain the non-sandbox boundary.

### Maintainer-script PATH

Canonical local owner: draft PR #109 / issue #107.

The caller's leading PATH components can remain ahead of apt's configured `DPkg::Path`, allowing a package script to resolve a caller-path command instead of the expected package-manager tool.

Estimated severity: **5/10** hardening, reproducibility, and compatibility.

Upstream readiness: **not ready**. Keep separate from `TMPDIR`. The current draft still needs exact-head proof for apt-managed and direct transactions, explicit configured-path authority, empty-value behavior, root/chrootless comparison, fakeroot, and environment compatibility.

## Tarfilter findings

Current upstream main still contains the main source shapes exercised by the local fixes: direct Python tar member mutation, raw slash splitting, partial PAX filtering, and transformation of member names without a complete metadata/link-target ownership contract.

### Higher-priority archive-integrity group

- stale PAX `path` or `linkpath` overriding rewritten fields;
- hard-link targets not following required name transformations;
- stale PAX ownership overriding id-shifted uid/gid;
- sparse member re-emission with inconsistent sparse/dense state or legacy type flags.

Estimated severity: **6/10 to 7/10**, depending on whether the affected archive is used as a trusted root filesystem or package/build artifact.

Upstream readiness: **good after current-main composition and focused dedup**. Submit one semantic defect per patch or a tightly ordered archive-metadata series. Preserve modes, type flags, PAX keys, link targets, sparse maps, and GNU tar controls.

### Lower-priority compatibility group

- legacy NUL regular-file type matching;
- empty slash segments in strip-components;
- negative strip-components validation;
- transform occurrence selection;
- basic versus extended transform regex dialects.

Estimated severity: **2/10 to 4/10** compatibility/correctness.

Upstream readiness: merged local fixes can be prepared independently; draft PR #151 still needs final exact-head review.

## Caching proxy findings

The helper is development/CI infrastructure, not a default installed network service. That limits practical exposure, but its current source has several overlapping correctness and containment problems.

### Request authority and cache-path containment

Canonical local owner: PR #118. PR #94 is superseded.

Potential consequences include cache-root escape through malformed request targets or pre-existing symlink parents, assertion removal under optimized Python, and unintended non-loopback exposure.

Estimated severity: **7/10 in the narrow exposed-helper scenario**, lower in ordinary loopback-only CI use.

Upstream readiness: **not yet**. Require exact-head green CI and then compose with the response-side stack before external submission.

### Cache publication, framing, short responses, origin status, and committed errors

Canonical local owners:

- merged PR #96: atomic publication and mode preservation;
- merged PR #120: downstream framing and hop-header normalization;
- merged PR #137: declared-length validation and retry recovery;
- merged PR #139: proxy/origin request-header separation;
- PR #162: canonical composition gate;
- PR #169: explicit origin-status validation under `python -O`;
- PR #147: no second response after downstream commitment.

Estimated severity: **4/10 to 6/10** cache integrity, availability, credential forwarding, and protocol correctness.

Upstream readiness: **blocked on one integrated current-main source state**. Isolated green patches are insufficient because they overlap in the same request/stream loop and already exposed a chunked-versus-Content-Length semantic conflict.

Submission shape, when ready: one small ordered series for `caching_proxy.py`, with request containment and loopback policy clearly separated from response/cache integrity where possible, plus one integration regression.

## File-mirror automount containment

Canonical local owner: PR #179.

The setup and cleanup hooks derive generated-root destinations from repository or package path text and persisted marker entries. Lexical traversal or a pre-existing destination-parent symlink can redirect setup or cleanup outside the generated root.

Estimated severity: **6/10 to 7/10** under attacker- or operator-controlled repository/include path input.

Upstream readiness: **high-priority after exact-head green CI**. Setup and cleanup must remain one patch because they share a persisted marker format and containment contract. State explicitly that same-UID path replacement races remain outside scope.

## Verifier wrapper

Canonical local owners:

- PR #138: preserve `gpgv` exit status instead of the output filter's pipeline status;
- PR #177: validate `--status-fd` forms and missing/repeated arguments;
- PR #180: signal forwarding and child reaping.

The present shell pipeline can report filter success after verifier failure. APT may independently reject familiar bad-signature status records, so this has not been demonstrated as a signature bypass, but unrecognized verifier failures or crashes must not become wrapper success.

Estimated severity:

- exit-status ownership: **6/10**;
- option parsing: **3/10**;
- signal forwarding/reaping: **3/10 to 4/10**.

Upstream readiness: PR #138 is a strong focused candidate after exact-current-main execution. Compose or sequence #177 and #180 deliberately rather than sending three competing wrappers.

## Proxysolver and lifecycle findings

Merged PR #134 preserves ordinary solver exit status. PR #166 preserves signal termination instead of converting a negative Python return code into an unrelated ordinary shell status.

Other open lifecycle fixes cover cancellation falling through to success or cleanup-only signal traps resuming work.

Estimated severity: **2/10 to 5/10**, primarily trustworthy automation and cancellation semantics.

Upstream readiness: small focused patches are appropriate after rebasing each follow-up on its canonical predecessor. Do not bundle unrelated wrappers and builders.

## Autopkgtest and Debian bug #1141078

### Existing upstream channel

The strongest immediate upstream contribution is the recovered `tests/dev-ptmx` fixture owner:

- the test runs `/usr/bin/script`;
- the generated root did not explicitly install its provider, `bsdutils`;
- `bsdutils` stopped being Essential;
- merged PR #89 retains the minimal dependency correction and regression.

Estimated severity: **2/10 to 3/10** package-test reliability, not product security.

Upstream readiness: **ready to add evidence to existing Debian bug #1141078 when external contact is authorized**. Send the minimal root cause, reproduction, patch, and regression; do not send PR #72 wholesale.

### Current-sid Deb822 and capability scheduling

PR #72 is a retired broad investigation carrier. Its Deb822 `sourcesfilter`
compatibility candidate is strongly reproduced on current sid, and its branch
and conversation retain the reduction history and reusable-tooling source. The
final run first failed at case 125 because `env --chdir` could not resolve the
temporary repository-relative `./mmdebstrap` proxy. Focused current-main slices
should carry any reusable tools. PR #171 owns the hard-failure scheduling
correction introduced while removing incompatible hooks.

Estimated severity: **2/10 to 4/10** package-test/tooling compatibility.

Upstream readiness: **not ready as one contribution**. Split stable harness work, Deb822 compatibility, and hook-free hard-failure scheduling into independent units after exact-current-head proof.

## Upstream action order if contact is later authorized

1. Update existing Debian bug #1141078 with the `bsdutils` fixture root cause and minimal patch.
2. Prepare the verifier exit-status fix as a small focused current-main patch.
3. Prepare file-mirror setup/cleanup containment as one focused current-main patch.
4. Prepare the highest-value tarfilter metadata/link/sparse fixes as small ordered patches.
5. Rebase the ordinary proxysolver status fix and its signal follow-up into a coherent small series.
6. Submit caching-proxy work only after the integrated stack is green.
7. Treat chrootless environment/PATH work as an explicit design and compatibility discussion, not as a surprise critical-vulnerability claim.
8. Never file the PR #74 `TMPDIR` regression as a standalone upstream defect.

Before every external action:

- fetch exact canonical upstream main;
- apply and run the exact patch against that source;
- search Debian BTS and the canonical upstream issue/MR tracker for duplicates;
- state the tested revision and environment;
- include one negative control;
- avoid severity inflation;
- disclose the exact boundary and non-claims;
- obtain explicit authorization for external contact.

## Current sprint closeout rules

Finalizable now:

- merge documentation-only handoff work after exact-head CI;
- close duplicate handoff carriers;
- close diagnostic PRs after their bounded question is answered;
- merge code only when the exact current head is green and its predecessor/composition contract is explicit;
- retain one canonical owner per finding.

Not finalizable now:

- PR #72 as a whole;
- PR #109 PATH policy;
- the full caching-proxy stack without composition;
- stacked verifier signal work without the exit-status base;
- any external submission without authority and current-main/dedup verification.

## Bottom line

The queue is large because one audit pass found many independent correctness boundaries, not because one giant critical vulnerability was discovered.

The highest narrow priorities are cache-path containment, file-mirror containment, tar metadata/link/sparse integrity, and verifier status ownership. They are approximately 6/10 to 7/10, not proven 9/10 or 10/10 events.

The small `TMPDIR` issue is already fixed internally, remains separate from `PATH`, and should not become a standalone upstream report.
