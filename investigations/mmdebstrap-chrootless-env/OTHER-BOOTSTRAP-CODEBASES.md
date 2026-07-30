# Adjacent Debian bootstrap and wrapper codebases

Date: 2026-07-30

Tracking: issues #40, #107, and #130; investigation PR #105; candidate PR #109; wrapper reviews PR #134 and PR #138.

## Purpose

This note inspects concrete source patterns in adjacent Debian tooling. The goal is not to copy another project's implementation mechanically. It is to identify which trust boundary each project assumes and which parts remain relevant to mmdebstrap's unusual chrootless mode.

## `pbuilder`: canonical builder PATH

The shipped `pbuilderrc` explicitly exports:

```sh
PATH=/usr/sbin:/usr/bin:/sbin:/bin
```

It describes this as the path used inside pbuilder.

Source: <https://sources.debian.org/src/pbuilder/0.228.7/pbuilderrc>

Reusable lesson:

- build/package execution receives a known system path rather than the caller's interactive prefix;
- the canonical path is explicit configuration, not the result of checking every inherited component.

Limit:

- pbuilder executes inside a dedicated build chroot. Its canonical PATH is one part of containment, not a substitute for containment.

## `schroot`: default PATH plus an execution-variable filter

Schroot's source defines a default environment filter that removes shell startup hooks, loader controls, locale-search controls, resolver controls, and terminal-information paths. Historical source also builds a default PATH when there is no user environment and removes the filtered variables before entering the PAM environment.

Sources:

- current default filter: <https://sources.debian.org/src/schroot/1.6.13-3/CMakeLists.txt>
- historical environment construction and removal: <https://sources.debian.org/src/schroot/1.0.5-1/sbuild/sbuild-auth.cc>

Reusable lessons:

- executable search controls and loader/interpreter controls are distinct from credential-name detection;
- a minimal default environment and a removal filter can coexist;
- user-environment preservation is an explicit mode, not an accidental default.

Limit:

- schroot provides an actual chroot/session boundary. Its filter list is useful precedent, but it does not prove that environment filtering makes host execution safe.

## `debootstrap`: inherited host PATH with chrooted package stages

The current debootstrap entrypoint:

- unsets `TMP`, `TEMP`, and `TMPDIR`;
- exports the inherited `PATH`;
- checks host tools through that path;
- later performs its package stages through a target chroot when the target is not `/`.

Source: <https://sources.debian.org/src/debootstrap/1.0.141/debootstrap>

Reusable lessons:

- variable omission has deliberate semantics and must be understood at each operation;
- host-tool discovery and target package execution are separate phases;
- recursive target cleanup is guarded by target-state checks and, on Linux, `--one-file-system` for its kill-target operation.

Non-reusable assumption:

- inheriting host PATH is not a precedent for mmdebstrap chrootless maintainer scripts. Debootstrap's package execution normally relies on a chroot boundary, while mmdebstrap chrootless intentionally removes that boundary.
- unsetting TMP variables is safe only in debootstrap's own context. The mmdebstrap review already proved that omission at a host-executed maintainer-script boundary can select host `/tmp`.

## `debuerreotype`: verifier owns process status

Debuerreotype's expiration-ignoring wrapper is Bash, not POSIX shell. When a status fd is present, it uses process substitution:

```bash
exec gpgv "$@" "$fd"> >(sed "$sedExpression" >&"$fd")
```

Source: <https://sources.debian.org/src/debuerreotype/0.15-1.1/scripts/.gpgv-ignore-expiration.sh>

Consequences:

- the wrapper process becomes `gpgv`, so verifier status and verifier signal termination remain the process outcome;
- the status filter transforms a secondary stream;
- filter failure is not collected as the wrapper status;
- the design requires Bash process substitution and is not a drop-in POSIX-shell solution.

Reusable lesson for PR #138:

- the producer/verifier should retain ownership of its process outcome;
- a byte-stream filter should not be able to induce a replacement verifier failure through a disappearing FIFO reader;
- deciding that filter failure matters requires an additional channel, but that channel must not feed failure back into the producer.

## `mmdebstrap` references to adjacent wrappers

The imported `gpgvnoexpkeysig` source itself names debuerreotype's wrapper and Debian derivatives census `fakegpgv` as similar implementations. This makes review of those references part of the local source contract rather than an unrelated comparison.

Source: <https://sources.debian.org/src/mmdebstrap/1.5.7-1%2Bdeb13u1/gpgvnoexpkeysig>

Observed design difference:

- imported mmdebstrap uses a POSIX pipeline, so the final filter owns the shell status;
- debuerreotype uses Bash process substitution plus `exec`, so the verifier owns the process status;
- the FIFO candidate in PR #138 tries to collect both statuses, but peer review showed that its reader lifecycle can feed failure back into the verifier and its wrapper-only signal path does not own the verifier process.

## Cross-codebase conclusions

1. **Canonical PATH is established practice at package/build boundaries.** Pbuilder supplies one explicitly; schroot supplies a default when constructing a minimal environment.
2. **Host PATH inheritance depends on a stronger surrounding boundary.** Debootstrap normally chroots package execution; it is not precedent for host-executed chrootless maintainer scripts.
3. **Environment filtering is layered with isolation.** Schroot's filter does not replace the chroot/session boundary.
4. **Producer status should remain producer-owned.** Debuerreotype's `exec gpgv` topology demonstrates that clearly, although it does not report filter failure.
5. **Different compatibility authorities must stay separate.** The caller environment can remain available to apt while dpkg receives apt's configured `DPkg::Path`.
6. **Omission is an operation-specific policy.** Debootstrap's `unset TMPDIR` and mmdebstrap's target-derived `TMPDIR` are both intentional in their own boundaries; neither is universally correct.
7. **Do not copy a mechanism without its containment assumptions.** Chroot-based behavior, Bash process substitution, and POSIX-shell wrappers have different process and filesystem contracts.

No Debian or external upstream contact was made or authorized by this review.
