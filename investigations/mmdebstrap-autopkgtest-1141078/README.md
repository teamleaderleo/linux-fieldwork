# mmdebstrap autopkgtest style-gate control

## In simple words

A real Debian sid package-test run reached `mmdebstrap`'s testsuite but stopped at `perltidy failed` before the historical operation associated with Debian bug #1141078.

The installed `mmdebstrap` package was built with an older formatting tool, while the current sid test environment supplied newer source-check behavior. `coverage.sh` applies perltidy, line-length, Perl::Critic, and POD checks to the command script before starting the behavioral matrix.

This focused control separates source-policy checks from installed-package behavior without changing the installed command: the temporary test source sets `SKIP_MMSCRIPT_CHECKS=yes`, keeps `CMD=mmdebstrap ...`, and leaves the remaining Python, shell, mirror, and behavioral checks enabled.

## Existing work and duplicate search

- Supersedes the stale broad draft PR #9 as the current execution carrier.
- Original contained run: `30514378292`.
- Original reproduction artifact digest: `sha256:1570f3670261ca41ea8b9976a052698e6cc906bee55006860404b3134427a37a`.
- The original run exited `6`; the testsuite reported `perltidy failed` before the target behavior.
- The first attempted wrapper control moved past perltidy but failed at `pod2man` because `coverage.sh` independently selected a local fake script for all mmdebstrap-specific source checks. That failed control is retained as harness evidence, not product evidence.
- This control does not change the imported `mmdebstrap` source or the installed `/usr/bin/mmdebstrap` package.

## Source and test map

`upstream/mmdebstrap/debian/tests/testsuite` runs `coverage.sh` with `CMD=mmdebstrap ...`, so behavioral invocations resolve to the installed package.

`coverage.sh` derives `MMSCRIPT` from `CMD` and applies mmdebstrap-specific source checks before running the rest of the source checks and behavioral matrix.

`installed-command-style-gate-control.patch` changes only the temporary diagnostic source:

1. add an explicit `SKIP_MMSCRIPT_CHECKS` guard around the mmdebstrap-script perltidy, line-length, Perl::Critic, and POD block;
2. set `SKIP_MMSCRIPT_CHECKS=yes` in the autopkgtest testsuite;
3. retain the original `CMD=mmdebstrap ...` behavioral command.

Black, ShellCheck, shfmt, mirror preparation, and every selected behavioral test remain active.

## Probe and assertions

`tests/test_mmdebstrap_autopkgtest_style_gate_control.py` requires:

- the patch applies to the exact imported testsuite and `coverage.sh`;
- the testsuite retains `CMD=mmdebstrap ...` while setting the explicit source-check override;
- the override guards only the mmdebstrap-script source block;
- no wrapper command is introduced;
- unsafe output paths are rejected before execution.

The dedicated workflow runs the full Debian sid autopkgtest in a disposable privileged container and uploads the console, exit status, source hashes, tool versions, patch application output, and autopkgtest output tree.

## Distinguishing outcomes

- `perltidy failed` or `pod2man` failure remains: the explicit guard did not isolate the intended source-only block.
- Source checks pass, then a later test fails: retain the first behavioral or infrastructure failure and identify its owning component.
- Full pass: the current sid package no longer reproduces the historical failure under this bounded control.
- Exit `77`: environment or package test returned a neutral result.

## Evidence limits

This is a diagnostic test-carrier patch, not a proposed Debian package change. It deliberately bypasses only the mmdebstrap-script source-policy block while preserving installed-command execution and the rest of the package suite.

It does not decide which formatter or policy Debian should use, and it does not by itself establish whether bug #1141078 still reproduces. The package test remains network- and mirror-dependent and may expose unrelated current sid failures after the source-policy block.

## Self-review

- The source under `upstream/` remains unchanged.
- `CMD` remains the installed `mmdebstrap` command.
- The override is explicit in both temporary source and retained provenance.
- Other source checks remain enabled.
- The temporary patched source and every changed input are hashed.
- Output and temporary source roots are guarded before recursive cleanup.
- The workflow retains failures rather than claiming only a green result.

## Reusable note

See `notes/debian/style-gates-can-mask-package-test-behavior.md`.

## Next step

Run the exact current-main carrier, inspect the first post-source-gate failure, and update this record with the run and artifact digest. No upstream contact is authorized.
