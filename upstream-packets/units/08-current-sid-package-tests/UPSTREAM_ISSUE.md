# Upstream issue draft

Use only when maintainers prefer an issue before a merge request. No publication is authorized.

## Title

Package tests stop on current sid before reaching independent mmdebstrap results

## Draft

The Debian package test currently encounters several compatibility and phase-order failures on current sid before it can classify later mmdebstrap behavior:

- `debian/tests/sourcesfilter` rejects Deb822 source entries;
- the broad test command needs a working-directory-independent installed-binary path;
- the customize-hook SIGINT case uses a process-group `kill` spelling rejected by current sid procps;
- `root-without-cap-sys-admin` receives a mount-dependent host APT hook after deliberately dropping `CAP_SYS_ADMIN`;
- that capability case consumes `tar1.txt`, which must be created under the same hook-free command configuration;
- the broad phase also needs its own `tar1.txt` regeneration under host APT hooks for later consumers.

A four-commit candidate addresses these as one ordered package-test series:

1. root raw source file paths before processing `SourcesList.exploded_list()`;
2. invoke `/usr/bin/mmdebstrap` for broad installed-package execution;
3. deliver process-group SIGINT through dash builtin `kill -s INT -- -PGID`;
4. classify only `root-without-cap-sys-admin` as a hook-free hard consumer, prepend `create-directory` in that focused phase, preserve ordinary failure statuses, and allow broad `create-directory` execution to regenerate the phase-local baseline.

Current-sid integration evidence from the composed carrier reached and passed the focused producer/consumer pair, later executed the broad producer again, completed 154 package tests, and then reached an independent `chrootless` directory-mtime result.

The proposed issue boundary is package-test compatibility and phase-local fixture identity. The later archive timestamp policy belongs in a separate discussion.

## Evidence to attach before publication

- exact current Salsa base and candidate head;
- zero-fuzz/zero-offset series application receipt;
- focused Deb822, SIGINT, hook-free producer/consumer, and broad regeneration results;
- current-sid package-test command, package versions, status, first independent result, and artifact digest;
- complete upstream diff and active-overlap review.
