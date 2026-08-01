# Source map

## Upstream identities

| Item | Identity | Role |
| --- | --- | --- |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` | intended upstream destination |
| Intended base | `main@77ec9be5417ee44c96343d2347145585da1b1f94` | current official head observed 2026-08-01 |
| Current Debian source | `mmdebstrap 1.5.7-3` | current sid/forky package source |
| Setup source | `hooks/file-mirror-automount/setup00.sh` | discovers repositories/packages, mounts or copies them, writes marker |
| Cleanup source | `hooks/file-mirror-automount/customize00.sh` | consumes marker, unmounts or removes targets |
| Setup baseline blob | `6ccbdaf2ba97c77c4e5223ac5280acd51a998424` | exact Linux Fieldwork import and packaged-source blob |
| Cleanup baseline blob | `b6b9b46afdd9dad01df3abcb514475326162e42c` | exact Linux Fieldwork import and packaged-source blob |

## Linux Fieldwork carriers

| Carrier | Exact role | Current use |
| --- | --- | --- |
| Issue #164 | owning defect and final bounded contract | canonical technical history |
| PR #179 | merged three-patch carrier and exact-head reviews | canonical implementation and test receipts |
| `investigations/mmdebstrap-file-mirror-containment/0001-contain-file-mirror-targets.patch` | source/destination containment, root refusal, marker discipline, cleanup preflight | first local increment |
| `investigations/mmdebstrap-file-mirror-containment/0002-preserve-file-uri-target-path.patch` | separates canonical host source from configured in-root URI path | second local increment |
| `investigations/mmdebstrap-file-mirror-containment/0003-reject-parent-uri-components.patch` | rejects every configured `..` component | third local increment |
| `investigations/mmdebstrap-file-mirror-containment/README.md` | durable investigation summary | evidence and policy source |
| `investigations/mmdebstrap-file-mirror-containment/WALKTHROUGH.md` | line-by-line lifecycle explanation | reviewer orientation |
| `notes/filesystems/cleanup-markers-must-carry-contained-relative-paths.md` | reusable cleanup lesson | rationale only |

## Executable regression ownership

| Test | Owned claim |
| --- | --- |
| `tests/test_file_mirror_automount_containment.py` | baseline traversal; valid repository/package mapping; target-parent symlink escape; source-symlink compatibility; marker format; valid and rejected cleanup |
| `tests/test_file_mirror_automount_root_guard.py` | literal `/` and symlink-to-`/` refusal before action |
| `tests/test_file_mirror_automount_cleanup_preflight.py` | mixed valid/invalid marker produces zero actions; marker retention; corrected rerun in root and non-root-style modes |
| `tests/test_file_mirror_automount_source_normalization.py` | harmless dot normalization; leading and embedded parent rejection |
| `tests/test_file_mirror_automount_parent_component_reachability.py` | predecessor unreachable-URI negative control and final parent-component policy |

## Packet files

| Path | Role |
| --- | --- |
| `patches/0001-file-mirror-automount-containment.patch` | mechanically composed current-upstream-path patch |
| `README.md` | current packet state and identities |
| `DEEP_DIVE.md` | mechanism, approach history, compatibility, remaining limits |
| `TESTS.md` | exact commands, hashes, results, cleanup, pending gates |
| `DECISIONS.md` | composition, policy, destination, and authority decisions |
| `UPSTREAM_ISSUE.md` | optional public issue draft; retained without submission |
| `UPSTREAM_PR.md` | public pull-request draft; retained without submission |
| `HANDOFF.md` | interruption-safe exact state |

## Adjacent carriers read and excluded

| Carrier | Why separate |
| --- | --- |
| Issue #153 / PR #158 | changes package-test phase selection for a capability-sensitive case; no hook source overlap |
| Issue #79 / PR #90 | changes local HTTP test-server readiness and cleanup; no hook source overlap |
| Issue #53 | owns Debian test dependency history and coordinates current-sid follow-ons; no file-mirror source correction |

## Composition map

```text
APT file: URI / local .deb path
              |
              v
setup00.sh: source identity + configured destination identity
              |
              v
mount / sync-in / upload
              |
              v
root-relative NUL marker
              |
              v
customize00.sh: full preflight -> immediate recheck -> umount/rm -r
```

Setup and cleanup belong in one submission because the marker is the authority transfer between them. Changing only setup leaves cleanup trusting historical or corrupted path text; changing only cleanup leaves setup able to act outside the generated root.
