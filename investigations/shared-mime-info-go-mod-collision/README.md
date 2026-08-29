# shared-mime-info classifies Go module files as Amiga audio

## In simple words

On Ubuntu 26.04, `xdg-mime` classifies an ordinary textual Go dependency file
named `go.mod` as `audio/x-mod`. The shared MIME database owns the broad `*.mod`
glob for Amiga SoundTracker modules, while `file --mime-type` independently
reports the same Go file as `text/plain`.

This is a real extension collision, but the correct upstream repair is still
open: a basename-specific Go MIME rule, content magic, consumer-side handling,
or deliberately retaining the generic audio glob may each have compatibility
effects. It is not proof of a GNOME LocalSearch extractor bug and is tracked
separately from the LocalSearch crash.

## Current state

- State: `SCOPING`
- Exact working head: Linux Fieldwork base `6f52e7166bbeb05814c94ab546ec1771d6fc5d0c`
- Latest authoritative gate or artifact: live `xdg-mime`, `file`, and installed
  shared MIME XML comparison
- First incomplete step: identify current upstream ownership/precedent for Go
  module MIME types and test rule precedence against real tracker modules
- Cleanup state: read-only probe; nothing to clean up
- Next safe action: build a small positive/negative corpus and test candidate
  MIME rules in a disposable database
- External-contact state: no upstream contact authorized or made

## Question

Can shared-mime-info distinguish the reserved Go basenames (`go.mod`, and
possibly related workspace/sum files) from genuine Amiga tracker `*.mod` files
without weakening established audio detection?

## Source

- Project: freedesktop.org shared-mime-info
- Package version: `shared-mime-info 2.4-5build3`
- Installed source data: `/usr/share/mime/packages/freedesktop.org.xml`
- Candidate source commit: none
- Local source path: not imported
- Import metadata: none

## Environment

- Distribution and release: Ubuntu 26.04.1 LTS
- Kernel and architecture: Linux `7.0.0-30-generic`, x86-64
- Host context: physical workstation (`big-red`)
- Privileges: unprivileged read-only classification

## Baseline behavior

For a real Go module file in a checked-out project:

```sh
xdg-mime query filetype /path/to/go.mod
# audio/x-mod

file --mime-type /path/to/go.mod
# /path/to/go.mod: text/plain
```

The installed freedesktop XML contains `*.mod` globs for module/audio types,
including a weight-40 entry and the Amiga SoundTracker rule. GNOME LocalSearch
therefore dispatched multiple Go module/cache files as `audio/x-mod` and logged
that it could not extract metadata from them.

## Hypotheses and discriminators

1. **Specific basename wins safely:** a high-weight `go.mod` rule classifies Go
   module manifests while genuine names such as `song.mod` remain audio.
2. **Content magic is required:** basename alone is insufficient because an
   audio file can legally be named `go.mod` or tooling recognizes more names.
3. **No shared type should be added:** downstream indexers should cheaply reject
   text that lacks tracker magic while shared-mime-info preserves compatibility.

The corpus must include at least one real Go manifest, one minimal syntactically
invalid textual `go.mod`, genuine tracker files covering common magic variants,
and text files named `song.mod`/`go.mod` as negative controls.

## Reproduction plan

1. Search current shared-mime-info issues, commits, tests, and MIME type registry
   for Go module precedent.
2. Record the exact upstream revision corresponding to or newer than the Ubuntu
   package.
3. Create a disposable MIME database and minimal public/synthetic corpus.
4. Compare baseline and candidate output from `xdg-mime`, `gio info`, and the
   shared-mime-info test tool.
5. Check that ordinary tracker modules preserve `audio/x-mod` and unrelated
   `.mod` ecosystems are not silently reclassified.

## Results

- Demonstrated: the installed shared MIME database classifies a real textual
  Go `go.mod` file as `audio/x-mod`.
- Demonstrated: `file` independently classifies that file as `text/plain`.
- Demonstrated: LocalSearch's audio extractor receives and rejects these files.
- Not demonstrated: the canonical MIME name for Go modules, the correct rule
  precedence, behavior of current upstream main, or any relation to the
  LocalSearch process crash.

## Evidence boundary

The current observation uses one Ubuntu package and one real Go file. No
upstream source checkout, candidate XML, MIME test suite, desktop/file-manager
compatibility check, or real tracker-module corpus has run. `file` is an
independent classifier, not an oracle for freedesktop policy.

## Next step

Find upstream precedent, then test the narrowest basename/content rule in a
disposable database against both Go and real tracker-module controls. Split
consumer-specific LocalSearch behavior into a successor only if the shared MIME
result is intentionally unchanged.

## Authority

Internal source research, synthetic fixtures, and candidate MIME rules in the
owned repository are authorized. No freedesktop.org issue, merge request,
comment, or other upstream interaction has been authorized or made.
