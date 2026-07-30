# Handoff: active mmdebstrap and cache-proxy work

Recorded: 2026-07-30 23:44 +08:00 / 2026-07-30 15:44 UTC

Repository main at handoff start: `e53ca8571c7fb87050b474c175ada155bd3ade1f`

## Authority and scope

This is an internal Linux Fieldwork handoff. No Debian, Ubuntu, GNU, Python, or other external issue, email, merge request, patch submission, comment, or review was created or authorized during this work.

Imported upstream source remains unchanged. Candidate fixes are retained as local patches, regressions, notes, and investigation records.

## What materially landed

High-signal merged fixes and retained evidence from this work period include:

- PR #74 — chrootless maintainer-script `TMPDIR` is derived from the selected target, created as `01777`, and refused when it is a symlink or non-directory;
- PR #77 — `tarfilter --type-exclude=REGTYPE` also excludes legacy NUL regular-file members;
- PR #78 — `tarfilter --idshift` removes stale PAX `uid`/`gid` strings so shifted ownership is preserved;
- PR #83 — `tarfilter --strip-components` ignores empty slash segments like GNU tar;
- PR #85 and PR #87 — GNU PAX and old-GNU sparse members are re-emitted with valid sparse/dense state and normalized regular-file type flags;
- PR #88 — negative `--strip-components` values are rejected instead of acting as Python reverse slices;
- PR #89 — the `dev-ptmx` test explicitly installs `bsdutils`, the provider of `/usr/bin/script`;
- PR #90 — the package-test HTTP server now has readiness, liveness, retained stderr, and reliable reaping;
- PR #96 — cache fills use permission-preserving unique temporary files and atomic final-name publication;
- PR #102 — numeric GNU tar transform occurrence selectors are supported;
- PR #112 — the accepted LF-12 reproducible package variance corpus was clean-promoted to current main;
- PR #120 — fresh proxy responses no longer forward chunk framing or hop-by-hop fields after `http.client` has decoded the body;
- PR #134 — `proxysolver` propagates ordinary nonzero solver exit status;
- PR #137 — short upstream responses with declared `Content-Length` do not poison the cache and can recover on retry;
- PR #139 — proxy credentials and connection-specific request headers are not forwarded to origins, while repeated safe fields are preserved;
- PR #158 — `root-without-cap-sys-admin` was moved away from incompatible host APT hooks. This merge is incomplete as a final scheduling contract; see PR #171 below.

## Central current investigation: PR #72

PR #72 is still a draft and must not be merged in its current form.

Current head: `10bc4f1e19db897dffa4853984c90a5adf89e8b4`

Latest authoritative workflow: `30551542868`

- `capture-bug-report`: success;
- `lab-tools`: success;
- `reproduce-mmdebstrap`: failure;
- retained artifact: `8765484385`;
- artifact digest: `sha256:0da65bdd591a7eac1fbac00215caebd371ad84379325940d0b5ea9a2307d6942`.

Artifact inspection completed after the original handoff. The previous head
`10bc4f1e19db897dffa4853984c90a5adf89e8b4` ran 77 cases and first failed
at `(125/284) cwd-directory-not-accessible-by-unshared-user`. Its command changes directory
to the deliberately inaccessible target and then invokes the temporary
installed-command proxy as `./mmdebstrap`; `env --chdir` therefore cannot find
that repository-relative proxy and reports `No such file or directory`. This
is a reduction-harness path defect. It provides no new mmdebstrap product
conclusion.

The run never reached the later hook-free phase, so it also provides no
execution evidence for `root-without-cap-sys-admin` under the temporary
`Needs-APT-Config` scheduling experiment. PR #171 remains the canonical
hard-failure scheduling correction.

The run reached real package-test execution. Earlier current-sid execution at run `30546575662` proved that the Deb822 repair moved the suite past:

- `help`;
- `man`;
- `version`;
- `(30/284) create-directory`;
- `(31/284) unshare-as-root-user`.

That run then first failed at `(41/284) root-without-cap-sys-admin` because the case deliberately removed `CAP_SYS_ADMIN` but the globally injected `file-mirror-automount` hook attempted a bind mount before the intended `/proc/self/fd` assertion.

PR #158 moved that case into a hook-free phase by setting `Needs-APT-Config: true`. The important review finding is that this existing phase maps ordinary failures to neutral exit `77`. Therefore PR #158 removes the incompatible hook but weakens the case's failure classification.

PR #171 is the required correction. It introduces a separate hook-free, hard-failure phase and preserves:

- status `0 -> 0`;
- status `1 -> 1`;
- status `2 -> 2`;
- timeout `124 -> 77`.

Current PR #171 head: `e7afe1e939465e578341f80656a8603bb5b6d9f9`

Current PR #171 CI run: `30558221806` — queued at handoff time.

Do not interpret a future PR #72 pass through the merged PR #158 scheduling as authoritative until PR #171's hard-failure correction is green and composed into the current-sid experiment.

### PR #72 diagnostics

Temporary diagnostic PR #167 was retargeted to the latest retained artifact `8765484385` and is now closed without merge.

- diagnostic head: `72e484630c29ff2057acdef228c925e9f5d9612d`;
- workflow run: `30558320795`;
- result: artifact inspection identified the case-125 relative-proxy path defect described above.

Its only job downloads the retained ZIP and prints bounded result files, final testsuite streams, case boundaries, and anchored failure signatures. It executes no artifact content and does not match the privileged reproduction guard.

The diagnostic executed no artifact content. Its bounded question is answered;
do not revive it.

Obsolete diagnostics PR #128 and PR #156 were closed during handoff cleanup.

### PR #72 caveats that remain even after the next case is known

- The temporary Perl proxy is useful for reduction but causes formatter, line-length, Perl::Critic, and POD gates to validate the proxy rather than the installed package. Final reusable tooling should remove it and prove the installed package passes the original preflight path.
- The PR bundles the reusable harness with source-copy compatibility patches. Prefer separating stable tooling from discovered product/test fixes before merge.
- The exact historical Debian run `72574145` is already owned by the missing `bsdutils` fixture dependency. Current-sid Deb822 behavior is a strong explanation for modern Debian/Ubuntu runs, but it is not the owner of that recovered historical failure.

## Active priority queue

### 1. PR #171 — preserve hard failure in hook-free capability phase

Why first: it corrects a semantic hole introduced by merged PR #158 and directly affects interpretation of PR #72.

Head: `e7afe1e939465e578341f80656a8603bb5b6d9f9`

CI: `30558221806`, queued at handoff.

Required action:

- require exact-head green CI;
- review that the new hard phase runs without `sourcesfilter` or `file-mirror-automount`;
- confirm ordinary nonzero statuses propagate unchanged and only timeout `124` becomes neutral `77`;
- then use this scheduling contract for the next PR #72 run.

### 2. PR #118 — explicit request validation and cache-root containment

PR #94 was closed and superseded by PR #118. Do not revive PR #94.

PR #118 head: `e2e08f08125af6d4cc0b96d9b8afebc4817be6c1`

CI: `30556525043`, queued at handoff.

The successor owns the full boundary:

- no assertion-based request validation;
- exactly one `Host`;
- zero or one zero-valued `Content-Length`;
- no `Transfer-Encoding`;
- case-insensitive hostname/effective-port authority matching;
- raw path components validated before `PurePosixPath` normalization;
- percent escapes rejected for this narrow Debian archive cache-key policy;
- empty, doubled, trailing, dot, parent, backslash, NUL, absolute, and symlink-escaping paths rejected;
- optimized Python (`python -O`) negative control;
- loopback-only listener;
- zero origin/cache activity for rejected requests.

If exact-head CI is green, review and merge PR #118 rather than PR #94.

### 3. PR #162 — canonical cache repair composition gate

Head: `3f7f3a7277cd74592c131b361ccd87e547d49b5d`

CI: `30555926795`, queued at handoff.

This is the composition gate for merged PRs #96, #120, and #137. The key integration finding is that declared-length validation must not use a conflicting `Content-Length` when `HTTPResponse.chunked` is true and `http.client` owns transfer decoding.

Required action:

- require exact-head green CI;
- verify synchronized misses, mode preservation, short-body retry, chunked-plus-conflicting-length behavior, EOF-framed responses, negative lengths, temporary cleanup, and server reaping all run against one composed source;
- do not treat isolated green PRs as proof that their overlapping patches compose.

### 4. PR #169 — origin status must not rely on `assert`

Head: `3ae3a6501653f273af25adae0279d072795e5a2f`

CI: `30557655364`, queued at handoff.

This reproduces optimized-Python behavior where the imported `assert (status, reason) == (200, "OK")` disappears, allowing an origin 404 to become downstream 200 and a persistent cache object.

Required action:

- require real `python -O` negative control;
- accept status code 200 regardless of reason phrase;
- reject non-200 before downstream commitment and cache publication;
- compose this check into the canonical cache stack only after its isolated boundary is green.

### 5. PR #179 — contain `file-mirror-automount` setup and cleanup targets

Head: `43a080f24df87ee93cafe0dade6c802593932cb3`

CI: `30557780301`, queued at handoff.

This is security-relevant. It treats local repository/package path text and persisted cleanup marker entries as untrusted, requires strict containment below the generated root during both setup and cleanup, and leaves invalid markers for diagnosis.

Review focus:

- setup and cleanup must use the same canonical destination rule;
- marker entries must be root-relative and NUL-delimited;
- invalid cleanup input must cause no `umount` or `rm -r`;
- pre-existing symlink escapes are covered, but same-UID check/open races remain outside scope.

### 6. PR #147 and the later cache stack

PR #147 owns post-commit failure handling: after a downstream 200 may have begun, the proxy must close rather than append a second 502 response.

After PR #162 is green, add PR #147, PR #118, PR #139, and PR #169 through an explicit composition gate rather than by assuming the patch order.

### 7. PR #109 — canonical chrootless maintainer-script PATH

This remains draft and high value, but do not rush it.

The candidate keeps apt's host-side caller environment while passing apt's configured `DPkg::Path` into the isolated chrootless dpkg/maintainer-script environment. It must still prove on the live head:

- apt-managed caller-path negative control;
- mutation that restores caller PATH and resolves the fake command;
- explicit non-empty `APT_CONFIG` authority control;
- explicit empty `DPkg::Path` fail-closed behavior;
- successful direct `run_essential()` transaction using a disposable local essential package;
- original environment, TMPDIR, root/chrootless, and fakeroot compatibility boundaries.

Do not call this universal path sanitization. The authority is the configured `DPkg::Path`, not path ownership/writability inspection.

## Other open code stacks worth continuing after the above

- PR #138 — preserve `gpgv` verifier exit status instead of returning the filter's pipeline status;
- PR #177 — validate missing, equals-form, repeated, and malformed `--status-fd` arguments;
- PR #180 — forward HUP/INT/TERM to the owned verifier, drain the FIFO, reap both children, and preserve signal-derived status;
- PR #166 — re-raise solver signal termination instead of mapping Python negative return codes to shell status 241;
- PR #143 — parent-only SIGINT in `coverage.py` must not fall through to success;
- PR #159 and PR #172 — signal cleanup handlers must terminate rather than resume work;
- PR #151 — GNU basic versus extended transform regex dialects;
- PR #92 — exact subordinate-ID account field matching.

Treat these as independent queues. Do not drag unrelated branches into one merge merely because CI capacity is available.

## Review lessons from this session

### 1. Patch artifacts are executable inputs

The most common false failure was a malformed retained unified diff. Several jobs stopped before semantic execution because hunk counts or anchors were wrong.

Always include an exact `patch --batch --forward -p1` regression against the imported source before launching a privileged or long-running job. Prefer generated diffs from complete source states over hand-counted hunks.

### 2. A green isolated patch is not a green product state

The cache fixes overlap in the same helper and stream loop. Composition exposed a real semantic conflict between chunked transfer decoding and unconditional `Content-Length` validation.

Use a composed-source gate whenever patches touch the same control-flow region or metadata contract.

### 3. Preserve compatibility details while fixing correctness

Atomic publication initially used `mkstemp()` and silently changed shared cache files from the baseline `0666 & umask` mode to `0600`. The final fix uses `os.open(..., O_CREAT | O_EXCL, 0o666)` and asserts effective mode.

Permissions, type flags, PAX keys, target paths, and signal statuses are part of behavior, not incidental implementation details.

### 4. Assertions are not runtime input validation

`python -O` removes assertions. Any validation affecting request authority, cache keys, origin status, or filesystem access must be explicit and tested in an optimized interpreter.

### 5. Distinguish harness, carrier, and behavior failures

A failed workflow is not automatically a product defect. Classify in this order:

1. checkout/bootstrap/tooling;
2. retained patch application;
3. formatter/lint/POD/source gate;
4. mirror/service readiness;
5. named behavioral case;
6. product or fixture owner.

PR #72 only became useful after it retained enough evidence to name the first failing case and command.

### 6. Do not neutralize failures while removing an incompatible setup

PR #158 correctly removed the hook contradiction but routed the case into a soft phase. PR #171 exists because scheduling and failure ownership are separate contracts.

### 7. Keep diagnostics disposable

Diagnostic PRs should never merge. Close them as soon as their bounded question is answered. PR #128 and PR #156 were closed during this handoff. PR #167 remains open only because its latest artifact parse was queued.

## Immediate pickup checklist

1. Treat head `10bc4f1e19db897dffa4853984c90a5adf89e8b4` as a relative-proxy harness failure at case 125.
2. Review current PR #72 head `4146f5f01d9e9474abd72a1308e0d919369401b0` and workflow `30577374058` before deciding the broad carrier.
3. Keep PR #171 as the owner of authoritative hook-free hard-failure scheduling.
4. Check PR #118 exact-head CI; merge only the successor, not PR #94.
5. Check PR #162 exact-head CI before extending the cache stack.
6. Check PR #169 and PR #179 exact-head CI.
7. Close stale/duplicate carriers instead of accumulating parallel owners.

## Final status at handoff

Completed cleanup:

- PR #128 closed without merge;
- PR #156 closed without merge;
- PR #94 already closed and superseded by PR #118.

Still intentionally open:

- PR #72 — current head `4146f5f01d9e9474abd72a1308e0d919369401b0` composes the hard-failure scheduling patch; exact-head workflow `30577374058` is in progress;
- PR #171 — required hard-failure scheduling correction, CI queued;
- PR #118 — canonical explicit request-validation/containment successor, CI queued;
- PR #162 — core cache composition gate, CI queued;
- PR #169 — explicit origin-status validation, CI queued;
- PR #179 — file-mirror setup/cleanup containment, CI queued.

Retired after evidence transfer:

- PR #167 — diagnostic question answered; closed without merge.

No upstream contact occurred.
