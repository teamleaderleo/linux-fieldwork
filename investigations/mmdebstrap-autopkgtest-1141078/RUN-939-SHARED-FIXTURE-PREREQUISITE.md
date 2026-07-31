# Run 939 shared-fixture prerequisite failure

State: `classified — real package execution, capability command passed, focused fixture incomplete`

PR: #72  
Exact head: `7ff6d07c19c8f84a83b7bcb214ff85b2ea1cb7b7`  
Workflow: `30633385029` / 939  
Generated merge: `073e9f94d2e28e2867b96654767af7b9b58fd40b`

## Result

Run 939 cleared the carrier boundary:

- changed-patch validation passed;
- all four retained patches applied with zero fuzz and zero offset;
- Python compilation and shell checks passed;
- unique repository discovery passed;
- the disposable Debian sid package job entered `autopkgtest`.

The dedicated hook-free hard phase selected only:

```text
(41/284) root-without-cap-sys-admin
```

The capability command itself completed successfully:

```text
setpriv --bounding-set=-cap_sys_admin mmdebstrap ... /tmp/debian-chroot.tar
```

The test then failed during its retained output comparison:

```text
diff: tar1.txt: No such file or directory
```

Phase summary:

```text
successfully ran 0 tests
failed 1 tests
```

Package result:

- status 6;
- first failed case `root-without-cap-sys-admin`;
- SIGINT case unexecuted;
- broad matrix unexecuted;
- soft transition phase unexecuted.

Artifact:

- ID `8794809068`;
- ZIP digest `sha256:4d67bf1548b105d061840130b740db362861ef60dca701c60f7cbe719e3de73c`;
- 30 retained files;
- console digest `sha256:181d84551894719ad3f656b28c0c7e96201de04bf4f1b2c54ea6d542a750bf36`.

## Classification

This is real package execution and a real focused-fixture failure. It does not reject the capability behavior: the `mmdebstrap` command returned success without `CAP_SYS_ADMIN` before the missing baseline file stopped the test.

The consumer reads two persistent shared files:

```text
tar1.txt
pkglist.txt
```

`tests/create-directory` is their exact producer:

```text
... >pkglist.txt
... >tar1.txt
```

That producer normally precedes case 41 in the broad ordered matrix. The focused invocation selected the consumer alone and severed the shared-state dependency.

## Repair

Mark both `create-directory` and `root-without-cap-sys-admin` with `Needs-Hook-Free-APT-Config: true`.

The hard selector then emits:

```text
create-directory
root-without-cap-sys-admin
```

within one `coverage.py --exitfirst` invocation and in original coverage order. Both cases become skipped in the later host-APT broad phase, avoiding duplicate execution.

Focused controls require exact selection order, producer writes, consumer reads, hard ordinary failure, timeout 124 to 77, zero-fuzz and zero-offset patch composition, and unchanged imported source.

## Decision boundary

A fresh package run can interpret capability behavior only after both focused cases execute. SIGINT and later broad results remain pending.

## Authority

Internal Linux Fieldwork and disposable sid package evidence only. External contact authorized: false.
