# mmdebstrap autopkgtest style-gate control

## In simple words

A real Debian sid package-test run reached `mmdebstrap`'s testsuite but stopped at `perltidy failed` before the historical operation associated with Debian bug #1141078.

The installed `mmdebstrap` package was built with an older formatting tool, while the current sid test environment supplied newer perltidy behavior. The testsuite uses one `CMD` value both as the command under behavioral test and as the source file passed through the source tree's style gate.

This focused control separates those two responsibilities without changing the installed program under test: a tiny temporary wrapper is style-checked from the test source directory and then executes `/usr/bin/mmdebstrap` for every behavioral invocation.

## Existing work and duplicate search

- Supersedes the stale broad draft PR #9 as the current execution carrier.
- Original contained run: `30514378292`.
- Original reproduction artifact digest: `sha256:1570f3670261ca41ea8b9976a052698e6cc906bee55006860404b3134427a37a`.
- The original run exited `6`; the testsuite reported `perltidy failed` before the target behavior.
- This control does not change the imported `mmdebstrap` source or the installed `/usr/bin/mmdebstrap` package.

## Source and test map

`upstream/mmdebstrap/debian/tests/testsuite` creates a fake local `./mmdebstrap` to prove the installed command is used. It then runs `coverage.sh` with `CMD=mmdebstrap ...`.

`coverage.sh` resolves the first word of `CMD` and applies perltidy to that file before running the behavioral matrix. With the installed command, current sid perltidy can reject packaging produced with an older formatter before any behavioral case begins.

`installed-command-wrapper.patch` changes only the temporary test carrier:

1. create `./mmdebstrap-under-test` in the autopkgtest work directory;
2. make that wrapper execute `/usr/bin/mmdebstrap "$@"`;
3. pass the wrapper path as `CMD`.

The style gate now sees the small current-source wrapper. Every behavioral execution still reaches the installed package.

## Probe and assertions

`tests/test_mmdebstrap_autopkgtest_style_gate_control.py` requires:

- the patch applies to the exact imported testsuite;
- the wrapper explicitly executes `/usr/bin/mmdebstrap`;
- the behavioral `CMD` uses `./mmdebstrap-under-test`;
- the old direct installed-command `CMD` is gone;
- unsafe output paths are rejected before execution.

The dedicated workflow runs the full Debian sid autopkgtest in a disposable privileged container and uploads the console, exit status, source hashes, tool versions, patch application output, and autopkgtest output tree.

## Distinguishing outcomes

- `perltidy failed` remains: the control did not successfully isolate the style gate.
- Style gate passes, then a later test fails: retain the first behavioral failure and identify its owning component.
- Full pass: the current sid package no longer reproduces the historical failure under this bounded control.
- Exit `77`: environment or package test returned a neutral result.

## Evidence limits

This is a diagnostic test-carrier patch, not a proposed Debian package change. It deliberately prevents a current formatter from judging an older installed script while preserving installed-command execution. It does not prove which formatter version Debian should use, whether the source package should vendor formatting output, or whether bug #1141078 still reproduces.

The package test remains network- and mirror-dependent and may expose unrelated current sid failures after the style gate.

## Self-review

- The source under `upstream/` remains unchanged.
- The wrapper has no option parsing or behavior of its own; it uses `exec` and forwards all arguments.
- The temporary patched source and every changed input are hashed.
- Output and temporary source roots are guarded before recursive cleanup.
- The workflow retains failures rather than claiming only a green result.

## Reusable note

See `notes/debian/style-gates-can-mask-package-test-behavior.md`.

## Next step

Run the exact current-main carrier, inspect the first post-style-gate failure, and update this record with the run and artifact digest. No upstream contact is authorized.
