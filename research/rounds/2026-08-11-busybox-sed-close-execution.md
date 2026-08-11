# 2026-08-11 BusyBox sed close execution

## TL;DR

The close-error model predicted by the earlier source review reproduced on the installed Debian BusyBox 1.37.0: a targeted `fclose()` error on the `sed -i` temporary output was ignored, `sed` exited `0`, and the transformed temp was published over the input.

The same injected error against BusyBox `dos2unix` exited `1` and preserved the original, matching the current-source comparison.

Detailed commands, shim, outputs, and evidence limits are in [`../../investigations/busybox-sed-inplace-close-failure/RESULTS.md`](../../investigations/busybox-sed-inplace-close-failure/RESULTS.md).

## Exact identities

Current source reviewed:

```text
vda-linux/busybox_mirror
7473045ad3504db9b421427a452fd9b146346306
```

Runtime executed:

```text
/usr/bin/busybox
BusyBox v1.37.0 (Debian 1:1.37.0-6+b8)
```

The relevant current-master `sed -i` sequence remains unchanged from the behavior modeled by the installed runtime: checked `fflush()`/`ferror()`, unchecked output `fclose()`, then replacement rename.

## Distinguishing results

- `sed -i` + synthetic output-close `EIO`: exit `0`, transformed output published.
- `sed -i.bak` + same error: exit `0`, transformed output published, original retained in `.bak`.
- `dos2unix FILE` + same error: exit `1`, original preserved, temp removed.
- normal `sed -i`: exit `0`, transformed output published.

The shim called the real `fclose()` first and overrode only the reported return for the targeted temp output. This proves the error-handling decision but deliberately does not simulate damaged persisted bytes.

## Execution interruption

An exact-current clone was attempted first and failed because the execution environment could not resolve `github.com`. That is an environment failure, not a BusyBox result. Source identity and current code were independently available through the GitHub connector.

## Disposition

Promote the bounded claim from source concern to reproduced error-handling defect:

> BusyBox `sed -i` can ignore a reported output `fclose()` failure, publish the temporary result over the input, and return success.

Keep real-storage consequence separate until a filesystem-backed delayed-close failure is demonstrated.

## Next action

Prepare the smallest current-master close-check candidate when an exact checkout is available, then run the deterministic close-error control, normal and backup `-i`, existing `sed.tests`, and code-size comparison.

## External-contact state

No upstream greenlight; no BusyBox contact was made.
