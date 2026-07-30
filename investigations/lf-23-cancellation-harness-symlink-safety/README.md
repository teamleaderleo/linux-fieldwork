# LF-23 output symlink confinement

## In simple words

PR #199 resolves the complete requested cancellation-harness output path before deciding whether recursive replacement is allowed. That ordering prevents either a final symlink or an ancestor symlink below `/tmp` or `/var/tmp` from granting deletion authority over a target elsewhere.

The original regression proves a direct repository child is rejected. This cross-review adds both symlink forms of the same safety boundary.

## Source and routing

- canonical safety candidate: PR #199
- reviewed base head: `b1e8aa4e9376e41962e456467c2f3fdcb38cae17`
- predecessor current-main parent: `a0ec62f64fd6a9ff2cc20b28142ec876c52a5145`
- predecessor hosted gate: Linux Fieldwork CI run `30578704079` / run 564
- independently green first proof head: `556c15c67b2978a1eae635a27f4b69986b4dc0e2`, run `30579993408` / run 596
- concurrent expanded proof source: `65ddf0fce71d46b7851c599a358a52a8cc3c279b`
- harness: `programmes/services-resources/lanes/LF-23-cancellation-subprocess-fd-cleanup/scouts/LF-SCOUT-PROC-01/artifacts/cancellation_harness.py`
- focused regression: `../../tests/test_lf23_cancellation_harness_symlink_safety.py`
- authority: internal Linux Fieldwork work only

## Regression

The focused test creates sentinel-bearing target directories below the checkout, outside every allowed cleanup root, then exercises two requests below a writable explicit disposable root (`/tmp` or `/var/tmp`):

1. the requested output itself is a symlink to the target;
2. an ancestor of the requested output is a symlink to the target.

The candidate must resolve the whole requested path before the descendant check, reject both requests with `output must be a child`, preserve each sentinel byte-for-byte, retain the symlinks, and create no output directory in the outside target.

The test subclasses the existing LF-23 safety class, so direct root refusal and direct repository-child preservation rerun in the same focused command:

```text
python3 -m unittest -v tests/test_lf23_cancellation_harness_symlink_safety.py
```

Complete discovery and exact-head Linux Fieldwork CI remain required on the canonical composed head after transfer.

## Evidence boundary

This proves decision-time resolution of final and ancestor symlink components. The harness still permits recursive replacement of an explicitly selected existing descendant of the artifact directory, `/tmp`, or `/var/tmp`. Same-UID mutation after validation remains governed by Python's Linux fd-based `shutil.rmtree` behavior and remains outside this focused test.

## Carrier history

Review PR #208 advanced concurrently while its first green proof was being transferred. The later two commits added the ancestor-symlink differential and tightened this record. Both unique changes were inspected and copied into canonical PR #199 before final closeout of the review carrier.

## External contact

No upstream contact was made or authorized.
