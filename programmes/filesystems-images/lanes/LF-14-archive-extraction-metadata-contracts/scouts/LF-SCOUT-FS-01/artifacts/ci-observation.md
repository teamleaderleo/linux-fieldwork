# CI observation

Pull request #17 reran Linux Fieldwork CI as run `30532386200` on Ubuntu 24.04 after the review fixes.

The LF-14 tests passed against the checked-out repository source:

```text
test_output_guard_rejects_destructive_root ... ok
test_reference_and_tarfilter_matrix ... ok
test_sparse_content_detector_rejects_wrong_extents ... ok
Ran 3 tests in 0.492s
OK
```

The matrix test regenerated all nine fixtures, ran the direct GNU tar path, rewrote the archives through `upstream/mmdebstrap/tarfilter`, asserted exact sparse contents and privilege-dependent extracted ownership, and confirmed the only failed contract was the filtered sparse case. The negative control proved that wrong sparse extent bytes fail the content predicate.

The overall `lab-tools` job later exited 1 in the existing command-help step at:

```sh
[[ -f scripts/capture-linux-context.sh ]] && \
  bash scripts/capture-linux-context.sh --help >/dev/null
```

No LF-14 file is involved in that later command. Python compilation and all unit tests completed successfully.
