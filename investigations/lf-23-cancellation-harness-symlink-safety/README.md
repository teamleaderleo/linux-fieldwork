# LF-23 output symlink confinement

## In simple words

PR #199 resolves the requested cancellation-harness output path before deciding whether recursive replacement is allowed. That ordering prevents a symlink placed below `/tmp` or `/var/tmp` from granting deletion authority over a target elsewhere.

The original regression proves a direct repository child is rejected. This cross-review adds the missing symlink form of the same safety boundary.

## Source and routing

- canonical safety candidate: PR #199
- reviewed exact head: `b1e8aa4e9376e41962e456467c2f3fdcb38cae17`
- current-main parent: `a0ec62f64fd6a9ff2cc20b28142ec876c52a5145`
- harness: `programmes/services-resources/lanes/LF-23-cancellation-subprocess-fd-cleanup/scouts/LF-SCOUT-PROC-01/artifacts/cancellation_harness.py`
- focused regression: `../../tests/test_lf23_cancellation_harness_symlink_safety.py`
- authority: internal Linux Fieldwork work only

## Regression

The test creates:

1. a sentinel-bearing target directory below the checkout, outside every allowed cleanup root;
2. a symlink named `output` below a writable explicit disposable root (`/tmp` or `/var/tmp`);
3. a harness invocation using that symlink as `--output`.

The candidate must resolve the symlink target before the descendant check, reject the request with `output must be a child`, preserve the sentinel byte-for-byte, and leave the symlink itself present.

The test subclasses the existing LF-23 safety class, so direct root refusal and direct repository-child preservation rerun in the same focused command:

```text
python3 -m unittest -v tests/test_lf23_cancellation_harness_symlink_safety.py
```

Complete discovery and exact-head Linux Fieldwork CI remain required before accepting the review enhancement.

## Evidence boundary

This proves resolution of a final-component symlink at decision time. The harness still permits recursive replacement of an explicitly selected existing descendant of the artifact directory, `/tmp`, or `/var/tmp`. Same-UID mutation after validation remains governed by Python's Linux fd-based `shutil.rmtree` behavior and is outside this focused test.

## Coordination repair

PR #199's tracked README still names earlier base and repair commits even though the current exact head and successful hosted run have advanced. Synchronizing that tracked record remains required before final promotion.

## External contact

No upstream contact was made or authorized.
