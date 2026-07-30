# CI observation

Pull request #17 triggered Linux Fieldwork CI run `30514461253` on Ubuntu 24.04.

The LF-14 test passed against the checked-out repository source:

```text
test_reference_and_tarfilter_matrix ... ok
Ran 1 test in 0.416s
OK
```

That test regenerated all nine fixtures, ran the direct GNU tar path, rewrote the
archives through `upstream/mmdebstrap/tarfilter`, and confirmed the only failed
contract was the filtered sparse case.

The overall `lab-tools` job later exited 1 in the existing command-help step at:

```sh
[[ -f scripts/capture-linux-context.sh ]] && \
  bash scripts/capture-linux-context.sh --help >/dev/null
```

No LF-14 file is involved in that later command. The compile step and unit-test
step both completed successfully.
