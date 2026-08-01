# Handoff

## Unit and state

- Unit: 20 — mmdebstrap tarfilter dotfile identity
- State: `ACTIVE`
- Worker: GPT-5.6 Thinking
- Linux Fieldwork branch: `upstream/unit-20-tarfilter-dotfile-identity`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact technical packet head before this handoff commit: `c1dafeb6c17622c6b2f13b72b33be0dfef4aca2c`
- External-contact state: unauthorized; internal work only

This `HANDOFF.md` commit follows the technical packet head and changes only the durable handoff. The exact final branch tip is recorded in the unit checkpoint on issue #397.

## Exact upstream identities

- Repository: `josch/mmdebstrap`
- Base branch: `main`
- Main head observed 2026-08-01: `77ec9be5417ee44c96343d2347145585da1b1f94`
- `tarfilter` last-change commit: `87b9b385b38795c58bc13ffb33b8724bed27f7a0`
- Imported source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Imported source SHA-256: `442b056aeb414aef0e33d59b6235623ca4d6072c62272508281d126cb3f3d957`
- Controlled upstream fork: `NEEDS FORK`
- Intended delivery: Forgejo fork and pull request

## Completed work

1. Read issue #397, packet README, packet index, issue #38, duplicate issue #28, issues #29 and #39, PR #33, the combined patches, focused tests, and the existing path-filter investigation.
2. Claimed unit 20 on issue #397.
3. Created branch `upstream/unit-20-tarfilter-dotfile-identity` from current Linux Fieldwork main.
4. Confirmed current upstream still contains `member.name.lstrip("./")`.
5. Split unit 20 from the older combined carrier.
6. Selected complete-prefix parsing that consumes leading `/` and `./` tokens while preserving filename dots and `..` components.
7. Added an upstream-style test and `coverage.txt` registration.
8. Retained the three-file patch at `patches/0001-tarfilter-preserve-dotfile-identity.patch`.
9. Ran a losing baseline, passing candidate, clean application, compilation, and immediate rerun.
10. Reviewed the complete diff and searched the public upstream issue/PR surface for active equivalent work.
11. Wrote the issue fallback, pull-request draft, decisions, source map, deep dive, test record, and receipts.

## Exact candidate identities

- Patch SHA-256: `2a62ae1ff84c1c613a0db89d1172e7f987164a472df0ea5da0e3b5b9037388c8`
- Candidate `tarfilter` SHA-256: `fdd55d9a6737bf1b5992da0254b0d6804f2b7f7598a385ed2f5b50f5196991de`
- Test SHA-256: `e9d4fc52860b718a6997c16770b98482c610a7016f0cd369c8da042ed113cc3d`

## Latest distinguishing result

```text
baseline upstream-style test: exit 1
candidate upstream-style test: exit 0
fresh patch application: exit 0, no fuzz or offset reported
python3 -m py_compile: exit 0
immediate clean rerun: exit 0
```

The baseline retained every `.config` spelling under `--path-exclude=/.config`. The candidate passes exclude and include checks for `.config`, `config`, `..name`, `...name`, repeated and alternating archive prefixes, and `../config`.

## Cleanup state

Temporary source copies, apply trees, generated archives, and test outputs were local scratch state. No process, mount, socket, lock, container, or generated archive remains intentionally active. Durable receipts and hashes are in `artifacts/`.

## First incomplete step

Obtain or create the controlled upstream checkout/fork, check out exact main `77ec9be5417ee44c96343d2347145585da1b1f94`, and run:

```sh
patch -p1 < upstream-packets/units/20-tarfilter-dotfile-identity/patches/0001-tarfilter-preserve-dotfile-identity.patch
CMD=./mmdebstrap ./coverage.py tarfilter-path-dotfiles
```

Record the exact fork repository, candidate branch, candidate commit, full runner output, cleanup, and rerun.

## Next safe action

Perform the complete-checkout application and registered focused test. Then review the exact three-file diff from the controlled fork. A clean result can advance the unit toward `READY FOR AUTHORIZATION`.

## Unexecuted gates

- registered `coverage.py` invocation in a complete current-upstream checkout;
- full `coverage.sh` suite;
- Debian package/autopkgtest execution;
- cross-version Python matrix;
- controlled-fork compare/diff and exact upstream candidate commit.

## Publication boundary

No upstream issue, pull request, comment, email, review, or other external contact has been created. Explicit authorization remains required.
