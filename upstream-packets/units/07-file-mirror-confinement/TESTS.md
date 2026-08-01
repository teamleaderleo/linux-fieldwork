# Tests and receipts

## Exact identities used

| Item | Value |
| --- | --- |
| Linux Fieldwork base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Official upstream base | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Baseline setup blob | `6ccbdaf2ba97c77c4e5223ac5280acd51a998424` |
| Baseline cleanup blob | `b6b9b46afdd9dad01df3abcb514475326162e42c` |
| Historical final carrier head | `6db473c5e3e462a93f9ba0bc975dbc46164f863b` |
| Historical exact-head CI | run `30580904313` / run 621 / job `91000593721` — success |
| Packet patch | `patches/0001-file-mirror-automount-containment.patch` |
| Packet patch SHA-256 | `928533ff01be39ba66c5350f7951706fd7f017448449c2671bb95a271db75f25` |
| Candidate setup SHA-256 | `f750be95ada2a3e39c972653158092f907f153ff0ca07c2200a326bcc11920be` |
| Candidate cleanup SHA-256 | `867443a4fd2737f5275c11180f1f17d6f7bc92d487e476327834764c06a8afc7` |

## Current-upstream identity check

### Sources consulted

- canonical Forgejo repository root and hooks directory;
- Debian sid source-package page for `mmdebstrap 1.5.7-3`;
- current packaged hook source mirror;
- Linux Fieldwork imported hook files and investigation identities.

### Result

The canonical repository reported `main@77ec9be5417ee44c96343d2347145585da1b1f94`. The hooks directory reported its latest file-mirror change as the 2024-03-23 warning-prefix commit. The current packaged setup and cleanup files have the same Git blob IDs recorded by the Linux Fieldwork import. No source rebase edit was required.

This establishes a clean current-source base for the packet. It does not claim that every remote mirror has identical repository metadata.

## Mechanical composition gate

A disposable tree was created with the exact baseline setup and cleanup bytes under:

```text
upstream/mmdebstrap/hooks/file-mirror-automount/
```

The retained patches were applied in order:

```text
patch --batch --forward -p1 -i p1.patch
patch --batch --forward -p1 -i p2.patch
patch --batch --forward -p1 -i p3.patch
```

Result:

```text
0001: exit 0; setup and cleanup patched
0002: exit 0; setup patched
0003: exit 0; setup patched; hunk succeeded with fuzz 1 after prior context movement
```

The fuzz is limited to unchanged helper context in the incremental local patch. The proposed packet patch was regenerated from exact baseline and final files, so it contains no fuzzy incremental dependency.

## Shell syntax gate

Commands:

```text
/bin/sh -n candidate/hooks/file-mirror-automount/setup00.sh
/bin/sh -n candidate/hooks/file-mirror-automount/customize00.sh
```

Result:

```text
setup00.sh: exit 0
customize00.sh: exit 0
```

## Fresh composed-diff gate

The final candidate files were diffed directly against the exact baseline paths:

```text
diff -u baseline/customize00.sh candidate/customize00.sh
diff -u baseline/setup00.sh candidate/setup00.sh
```

The headers were normalized to upstream paths under `hooks/file-mirror-automount/` and retained as one patch.

Receipt:

```text
size: 6707 bytes
sha256: 928533ff01be39ba66c5350f7951706fd7f017448449c2671bb95a271db75f25
```

## Historical fake destructive-command matrix

PR #179 exact head `6db473c5e3e462a93f9ba0bc975dbc46164f863b` passed Linux Fieldwork CI run `30580904313`. The five focused regressions cover:

| Scenario | Baseline | Candidate |
| --- | --- | --- |
| `file:///../../etc` | fake mount target escapes root | rejected before action or marker |
| ordinary repository | textual mount/copy | canonical source at contained configured target |
| local package | textual target | canonical source and contained destination |
| destination-parent symlink | can redirect outside | rejected before action |
| generated root `/` or symlink-to-`/` | host tree accepted as root | refused before command or marker processing |
| terminal source symlink | first repair broke configured URI | canonical source mounted at configured URI path |
| harmless `.` component | path spelling normalizes | accepted and reachable |
| leading or embedded `..` | traversal or unreachable normalized path | rejected before action |
| valid marker then invalid marker | partial cleanup possible | zero fake destructive actions |
| corrected marker rerun | diagnostic state uncertain | immediate successful rerun; marker retired |
| symlink escape in marker | host target possible | zero action; marker retained |

The fake commands include `mount`, `umount`, and destructive `rm -r`; tests use temporary directories and reap their disposable state.

## Cleanup and rerun for this pass

- disposable patch-composition directory: created under the tool runtime temporary directory and left only inside the ephemeral analysis runtime;
- real mounts/unmounts: none;
- sockets/listeners/process groups: none;
- packages/containers/images: none;
- source tree modification outside the unit branch: none;
- retained state: unit branch, packet files, and packet patch only.

The patch stack was applied once to a fresh tree. Both final scripts passed syntax immediately after composition. A second fresh-tree packet-patch application remains an explicit pending gate.

## Tests not run in this pass

- complete five-file fake destructive-command matrix against the single packet patch;
- packet patch `patch --dry-run` and apply on a freshly downloaded canonical Forgejo archive at the exact full commit;
- hosted Linux Fieldwork CI for the final packet head;
- real privileged bind mount/unmount fixture;
- real non-root hook-socket transfer;
- portability outside GNU `realpath` and GNU `xargs`;
- hostile concurrent path replacement after validation.

## Next exact test command

From a checkout of this unit branch:

```text
python3 -m unittest \
  tests.test_file_mirror_automount_containment \
  tests.test_file_mirror_automount_root_guard \
  tests.test_file_mirror_automount_cleanup_preflight \
  tests.test_file_mirror_automount_source_normalization \
  tests.test_file_mirror_automount_parent_component_reachability
```

Before treating that as packet-exact evidence, adapt the fixture to apply `upstream-packets/units/07-file-mirror-confinement/patches/0001-file-mirror-automount-containment.patch` directly to upstream-path copies, or add a focused packet-patch equivalence test.
