# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Upstream base | mmdebstrap `main` `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Baseline helper | blob `83370755454a1322bf6862751aab7381d175aa8b` |
| Retained patch | blob `a30b37ca1228df1d80fd7611d4a591549314aeb0` |
| Candidate helper | blob `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed` |
| Linux Fieldwork branch | `upstream/unit-03-gpgvnoexpkeysig-lifecycle` |
| Platform | Linux 6.12.13 x86_64 |
| Shell/runtime | `/bin/sh` syntax; `dash`; Python 3.13.5 available |
| Privilege boundary | disposable local files and isolated APT directories; no chroot, mount, namespace, or network required |
| GnuPG | `gpg (GnuPG) 2.4.7`; `gpgv (GnuPG) 2.4.7` |
| APT | `apt 3.0.3 (amd64)` |
| Fixture script digest | SHA-256 `dce709f2aeca82a2e0d38b427a1fd3aaff0b0c8a6deea1b80b3f13d91d6e6e98` |
| Release fixture digest | SHA-256 `0c17479259d62505307d0f8df9759195a724a6f2e2900dc56c15e10104918dcc` |

## Exact command

From the repository root:

```sh
./upstream-packets/units/03-gpgvnoexpkeysig-lifecycle/scripts/run-real-gpg-fixture.sh
```

The runner creates a disposable source tree, applies the retained patch with `patch -p1`, verifies exact Git blob identities, checks `/bin/sh -n`, generates a historical expired key, signs `fixtures/Release`, runs direct/baseline/candidate verifier cases through fd 3, creates a local APT repository, runs isolated `apt-get update` through both wrappers, checks candidate temporary directories, and deletes all generated state.

## Baseline reproducer

### Expected distinguishing result

A tampered payload should make real `gpgv` return nonzero with `BADSIG`. The current pipeline wrapper is expected to return the successful `sed` status 0.

### Observed result

First run:

```text
direct_badsig_rc=1
baseline_badsig_rc=0
direct_badsig_status=[GNUPG:] BADSIG BC128341BFCB45C5 Linux Fieldwork Unit 03 <unit03@example.invalid>
```

Rerun:

```text
direct_badsig_rc=1
baseline_badsig_rc=0
direct_badsig_status=[GNUPG:] BADSIG 4E40D9FA91A683D2 Linux Fieldwork Unit 03 <unit03@example.invalid>
```

- status: baseline incorrectly returned 0 after real `gpgv` returned 1;
- stdout: empty, because GnuPG status was routed to fd 3;
- stderr: normal GnuPG verification diagnostic only;
- changed state: none retained;
- artifact: `artifacts/real-gpg-fixture.txt`.

## Candidate reproducer

### Expected result

The candidate should return the direct verifier result, preserve `BADSIG`, keep status on fd 3, and remove its private spool state.

### Observed result

First run:

```text
candidate_badsig_rc=1
candidate_badsig_status=[GNUPG:] BADSIG BC128341BFCB45C5 Linux Fieldwork Unit 03 <unit03@example.invalid>
candidate_tmpdirs_empty=yes
result=PASS
```

Rerun:

```text
candidate_badsig_rc=1
candidate_badsig_status=[GNUPG:] BADSIG 4E40D9FA91A683D2 Linux Fieldwork Unit 03 <unit03@example.invalid>
candidate_tmpdirs_empty=yes
result=PASS
```

## Real expired-key result

The generated key is created at fake time 2000-01-01 00:00 UTC with one-day expiry and signs the fixture at 01:00 UTC. Verification at current time yields a real expired-key status.

First run:

```text
direct_expired_rc=0
baseline_expired_rc=0
candidate_expired_rc=0
direct_expired_status=[GNUPG:] EXPKEYSIG BC128341BFCB45C5 Linux Fieldwork Unit 03 <unit03@example.invalid>
candidate_expired_status=[GNUPG:] GOODSIG BC128341BFCB45C5 Linux Fieldwork Unit 03 <unit03@example.invalid>
```

Rerun:

```text
direct_expired_rc=0
baseline_expired_rc=0
candidate_expired_rc=0
direct_expired_status=[GNUPG:] EXPKEYSIG 4E40D9FA91A683D2 Linux Fieldwork Unit 03 <unit03@example.invalid>
candidate_expired_status=[GNUPG:] GOODSIG 4E40D9FA91A683D2 Linux Fieldwork Unit 03 <unit03@example.invalid>
```

The fingerprint changes because each run generates a new disposable key. The asserted status class and exit behavior remain stable.

## Local APT integration

The runner creates a minimal `file:` repository with an empty `Packages` index, writes MD5 and SHA-256 fields into `Release`, clear-signs `InRelease` with the expired key, and invokes:

```text
apt-get ... -o Apt::Key::gpgvcommand=WRAPPER update
```

Observed on both runs:

```text
baseline_apt_expired_rc=0
candidate_apt_expired_rc=0
```

Both isolated list directories reached `Reading package lists...`; no network mirror or system APT state was used.

## Matrix

| Case | Baseline | Candidate | Exact test | Result identity |
| --- | --- | --- | --- | --- |
| Patch application | n/a | clean, exact candidate blob | fixture setup | `8337075...` -> `de7e0ae...` |
| Shell syntax | pass | pass | `/bin/sh -n` in runner | both runs |
| Real expired signature | 0, rewrites to `GOODSIG` | 0, rewrites to `GOODSIG` | direct/baseline/candidate expired case | both runs |
| Real tampered signature | **0 after direct gpgv 1** | 1 | direct/baseline/candidate badsig case | distinguishing control |
| Status descriptor | status on fd 3; stdout empty | status on fd 3; stdout empty | wrapper invocation `--status-fd 3` | both runs |
| Local APT update | 0 | 0 | isolated `apt-get update` | both runs |
| Candidate cleanup | n/a | direct and APT TMPDIRs empty | `find ... -mindepth 1` | both runs |
| Immediate rerun | same defect | pass | complete script repeated | PASS |

## Previously executed canonical gates

PR #196 at final head `bc8d88089d931cd0b78dd0c95dd72c784195fcdc` recorded Linux Fieldwork CI run `30578936718` as passed. Its repository suite included:

- the eight-test canonical parser/status/signal matrix;
- verifier statuses 0, 1, and 2;
- immediate filter exit after a 20,000-record stream;
- explicit status-fd routing;
- malformed/missing/repeated option forms;
- HUP/INT/TERM wrapper-only delivery;
- deterministic verifier and filter launch-registration windows;
- blocking-filter termination;
- post-filter late-signal duplicate replay control;
- cleanup and immediate rerun;
- Python compilation, shell syntax, full unit discovery, and command-help checks.

Those results belong to PR #196's exact candidate head. The new fixture confirms that the same retained patch still applies and behaves correctly against the current unchanged helper source.

## Patch application and rebase

- current upstream base: `77ec9be5417ee44c96343d2347145585da1b1f94`;
- helper's current displayed latest commit: `59e5870e7b76cc25dc6cb7b34586451d4ec2a524`;
- baseline blob: `83370755454a1322bf6862751aab7381d175aa8b`;
- command: `patch -s -d "$SOURCE_TREE" -p1 < "$PATCH"`;
- result: clean application, no prompts, no fuzz, no offsets, candidate blob `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed`;
- complete diff: previously reviewed in PR #196 and re-read for this packet;
- active overlap: indexed upstream issue/PR/helper-name search found no equivalent active correction on 2026-08-01.

## Cleanup and rerun

The script traps EXIT/HUP/INT/TERM and removes its single top-level `unit03-real-gpg.*` directory. Candidate-specific direct and APT TMPDIRs were asserted empty before the top-level cleanup. Generated key homes, signatures, keyrings, local repository, APT lists, APT cache, source copies, status files, stdout/stderr captures, and result files were removed. The complete command passed immediately a second time.

## Tests not run

- Full upstream `coverage.sh`: broad mirror/chroot suite, outside the focused helper fixture and unavailable without a complete upstream checkout/cache.
- Remote historical snapshot transaction: avoids network dependency; the generated fixture exercises the same genuine `EXPKEYSIG` status locally.
- Additional `/bin/sh` implementations: current evidence uses the established `dash` target.
- Disk-full and temporary-filesystem failure injection.
- Multiple competing rapid signals.
- Signal-ignoring verifier/filter and descendant process groups.
- Controlled upstream branch CI: requires authorization to create the fork and branch.

## Failure classification

- Baseline tampered-signature red comparison: product failure in wrapper result ownership.
- Initial mock-repository script check during development: fixture packaging error caused by a locally generated patch path `a/a/...`; corrected before committed evidence. The retained repository patch already uses `a/upstream/...` and the final runner passed twice.
- No candidate execution failure remained in the retained receipts.

## Final evidence statement

On the exact current helper source, the retained lifecycle patch applies cleanly and produces the expected candidate blob. A real expired GnuPG key confirms the intended `EXPKEYSIG` rewrite and a real tampered signature confirms the baseline's false success and candidate's preserved status 1. A local APT transaction confirms the wrapper remains usable through `Apt::Key::gpgvcommand`. The conclusion covers GnuPG 2.4.7, APT 3.0.3, Linux x86_64, the current helper bytes, and the recorded POSIX-shell candidate; broader process-policy and platform questions remain explicit.
