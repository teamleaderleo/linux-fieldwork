# Unit 20 — tarfilter dotfile identity

## State

- Initiative: Linux Fieldwork issue #397, unit 20
- State: `ACTIVE`
- Linux Fieldwork branch: `upstream/unit-20-tarfilter-dotfile-identity`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- External-contact state: unauthorized; internal work only
- Upstream destination: Muffin Forgejo fork and pull request
- Controlled upstream fork: `NEEDS FORK`

## Exact upstream identities

- Project: `josch/mmdebstrap`
- Intended base branch: `main`
- Main head observed 2026-08-01: `77ec9be5417ee44c96343d2347145585da1b1f94`
- `tarfilter` last-change commit: `87b9b385b38795c58bc13ffb33b8724bed27f7a0`
- Imported source path: `upstream/mmdebstrap/tarfilter`
- Imported source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Imported source SHA-256: `442b056aeb414aef0e33d59b6235623ca4d6072c62272508281d126cb3f3d957`

## Selected candidate

- Patch: `patches/0001-tarfilter-preserve-dotfile-identity.patch`
- Patch SHA-256: `2a62ae1ff84c1c613a0db89d1172e7f987164a472df0ea5da0e3b5b9037388c8`
- Candidate `tarfilter` SHA-256: `fdd55d9a6737bf1b5992da0254b0d6804f2b7f7598a385ed2f5b50f5196991de`
- Upstream-style regression: `tests/tarfilter-path-dotfiles`
- Test SHA-256: `e9d4fc52860b718a6997c16770b98482c610a7016f0cd369c8da042ed113cc3d`

The patch replaces character-set stripping with complete-prefix parsing. It removes leading `/` and `./` archive syntax prefixes while preserving dots that belong to the first pathname component. It also registers a focused upstream test.

## Latest distinguishing evidence

- Baseline upstream-style test: exit `1`; `/.config` retained every dotfile spelling.
- Candidate upstream-style test: exit `0`.
- Fresh application and immediate rerun: exit `0`.
- Patch application: exit `0`, with no fuzz or offset reported.
- Python compilation: exit `0`.

See `TESTS.md` and `artifacts/` for commands, output, and hashes.

## Scope boundary

This unit owns only matching-path normalization and the corresponding include/exclude regression. It excludes:

- no-option passthrough, owned by unit 18 / issue #29;
- parent metadata retention, owned by unit 21 / issue #39;
- sparse archive rewriting;
- transform, strip, PAX, link-target, and type-filter semantics.

The older PR #33 combined those behaviors. This packet extracts the smallest independent source change and test.

## First incomplete step

Apply the retained patch in a complete checkout at upstream main `77ec9be5417ee44c96343d2347145585da1b1f94`, then run the registered test through the upstream runner:

```sh
CMD=./mmdebstrap ./coverage.py tarfilter-path-dotfiles
```

After that, review the exact three-file diff from a controlled fork branch and update the packet toward `READY FOR AUTHORIZATION`.
