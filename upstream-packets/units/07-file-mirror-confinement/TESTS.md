# Tests and receipts

## Exact identities used

| Item | Value |
| --- | --- |
| Linux Fieldwork base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Canonical upstream head observed | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Controlled fork | `teamleaderleo/mmdebstrap` |
| Fork base | `master@574048f2a720057b75e56622003932f344dc700a` |
| Fork candidate branch | `linux-fieldwork/unit-07-file-mirror-confinement` |
| Fork candidate head | `8b8dce6910badeda1e72e28f471fa220a22eea7d` |
| Baseline setup blob | `6ccbdaf2ba97c77c4e5223ac5280acd51a998424` |
| Baseline cleanup blob | `b6b9b46afdd9dad01df3abcb514475326162e42c` |
| Candidate setup Git blob | `80bf3f3ef4f5535ca802d91ac8bc6f3c2999a70c` |
| Candidate cleanup Git blob | `30ff2c56d83b5bedd91ec62e65f4c6a18bd4a6f6` |
| Packet patch | `patches/0001-file-mirror-automount-containment.patch` |
| Packet patch SHA-256 | `928533ff01be39ba66c5350f7951706fd7f017448449c2671bb95a271db75f25` |
| Candidate setup SHA-256 | `f750be95ada2a3e39c972653158092f907f153ff0ca07c2200a326bcc11920be` |
| Candidate cleanup SHA-256 | `867443a4fd2737f5275c11180f1f17d6f7bc92d487e476327834764c06a8afc7` |
| Reusable matrix | `scripts/test_candidate_hooks.py` |
| Matrix script SHA-256 | `a3da8cd22454e1f42b9328ad1f3cc0c372062b668e97e815a48aa160cdc166a0` |
| Historical carrier head | `6db473c5e3e462a93f9ba0bc975dbc46164f863b` |
| Historical exact-head CI | run `30580904313` / job `91000593721` — success |

## Current-source and fork identity check

The controlled fork baseline files were fetched from `master@574048f2a720057b75e56622003932f344dc700a`.

```text
hooks/file-mirror-automount/setup00.sh
Git blob: 6ccbdaf2ba97c77c4e5223ac5280acd51a998424

hooks/file-mirror-automount/customize00.sh
Git blob: b6b9b46afdd9dad01df3abcb514475326162e42c
```

These equal the packet baseline and Linux Fieldwork imported source identities. No rebase edit was required for the fork.

## Fork candidate creation

Branch:

```text
teamleaderleo/mmdebstrap
linux-fieldwork/unit-07-file-mirror-confinement
```

Commits:

```text
b18095f0a9916ad70872f6740ffae033fda9b034
file-mirror-automount: confine setup targets

8b8dce6910badeda1e72e28f471fa220a22eea7d
file-mirror-automount: preflight cleanup markers
```

Complete comparison against `master`:

```text
status: ahead
behind_by: 0
ahead_by: 2
changed paths: 2

hooks/file-mirror-automount/setup00.sh
  +78 -27
hooks/file-mirror-automount/customize00.sh
  +37 -17
```

No other path changed.

## Shell syntax and exact-byte gate

Commands:

```text
/bin/sh -n hooks/file-mirror-automount/setup00.sh
/bin/sh -n hooks/file-mirror-automount/customize00.sh
sha256sum hooks/file-mirror-automount/setup00.sh \
  hooks/file-mirror-automount/customize00.sh
```

Result:

```text
setup syntax: exit 0
cleanup syntax: exit 0
setup sha256: f750be95ada2a3e39c972653158092f907f153ff0ca07c2200a326bcc11920be
cleanup sha256: 867443a4fd2737f5275c11180f1f17d6f7bc92d487e476327834764c06a8afc7
```

The candidate hashes equal the packet composition receipts.

## Reusable fork-candidate matrix

Script:

```text
upstream-packets/units/07-file-mirror-confinement/scripts/test_candidate_hooks.py
```

Exact command executed against the fork candidate bytes reconstructed from the committed contents:

```text
python3 scripts/test_candidate_hooks.py \
  --setup /tmp/unit07-candidate/setup00.sh \
  --cleanup /tmp/unit07-candidate/customize00.sh
```

Result: exit `0`.

```json
{
  "cleanup_sha256": "867443a4fd2737f5275c11180f1f17d6f7bc92d487e476327834764c06a8afc7",
  "count": 10,
  "results": [
    "shell-syntax",
    "traversal-rejected",
    "root-refused",
    "ordinary-repository",
    "symlink-uri-reachable",
    "parent-component-rejected",
    "package-contained",
    "cleanup-preflight-rerun-root",
    "cleanup-preflight-rerun-fakechroot",
    "cleanup-symlink-rejected"
  ],
  "setup_sha256": "f750be95ada2a3e39c972653158092f907f153ff0ca07c2200a326bcc11920be"
}
```

The script uses disposable directories and fake `apt-get`, `mount`, `umount`, and destructive `rm -r` commands. It performs no real mount, unmount, package mutation, socket activity, namespace creation, or external network access.

### Cleanup and rerun result

For both `root` and `fakechroot` modes:

- a valid marker followed by `../../outside` caused zero fake destructive actions;
- the marker and valid target remained available for diagnosis;
- replacing the marker with the valid entry produced exactly one expected fake action;
- the marker was retired only after success;
- an immediate second cleanup returned success without another action.

A marker resolving through an in-root symlink to an outside path was rejected with zero fake actions and retained state.

## Historical broader matrix

PR #179 exact head `6db473c5e3e462a93f583e7c33a76a93ed1102b8` passed Linux Fieldwork CI run `30580904313`. Its five focused regressions additionally preserve the predecessor differential and complete investigation history.

## CI status

At the time of this receipt, GitHub reported no combined status checks attached to fork candidate head `8b8dce6910badeda1e72e28f471fa220a22eea7d`.

## Cleanup inventory

- real mounts/unmounts: none;
- sockets/listeners/process groups: none;
- packages/containers/images: none;
- temporary roots and fake command logs: removed by `TemporaryDirectory`;
- retained state: controlled fork branch, Linux Fieldwork packet branch, patch, script, and records.

## Tests still pending

- hosted CI attached to fork candidate head;
- application to a freshly downloaded canonical Forgejo tree at `77ec9be5417ee44c96343d2347145585da1b1f94`;
- final active-equivalent overlap search immediately before authorization;
- real privileged bind mount/unmount fixture;
- real non-root hook-socket transfer;
- portability outside GNU `realpath` and GNU `xargs`;
- hostile concurrent pathname replacement after validation.

## Next exact command

From checkouts of Linux Fieldwork and the controlled fork:

```text
python3 \
  linux-fieldwork/upstream-packets/units/07-file-mirror-confinement/scripts/test_candidate_hooks.py \
  --setup mmdebstrap/hooks/file-mirror-automount/setup00.sh \
  --cleanup mmdebstrap/hooks/file-mirror-automount/customize00.sh
```

Run it with the fork checkout on candidate head `8b8dce6910badeda1e72e28f471fa220a22eea7d` and retain the exact stdout plus repository identities.
