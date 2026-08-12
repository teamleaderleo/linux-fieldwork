# crun propagation fallback regression-test design

Date: 2026-08-12

Tracking: `teamleaderleo/linux-fieldwork#602`

## TL;DR

crun's current propagation tests exercise the successful `mount_setattr()` path. The stale-path defect only appears when that operation fails and `do_mount()` drops into legacy `mount(2)` propagation.

The existing Python harness already provides a low-ceremony way to test the fallback: `tests/tests_utils.py` resolves the runtime from the `OCI_RUNTIME` environment variable. A tiny wrapper can therefore install a seccomp filter that returns `ENOSYS` only for `mount_setattr()`, then `execv()` the real crun named by `REAL_CRUN`.

Tracked helper: [`mount-setattr-deny-wrapper.c`](mount-setattr-deny-wrapper.c).

This preserves ordinary crun source behavior while forcing the new-mount-API capability boundary from outside the process. `open_tree()`, `move_mount()`, and legacy `mount(2)` remain allowed, so the fixture specifically exercises crun's own fallback routing.

## Existing tests that already assert propagation

Current `tests/test_mounts.py` at `containers/crun@86e7e3eaf8e8d15e6e9983faddeffd0ea0771a94` includes:

- `test_mount_propagation_private()` — visible bind mount must not carry `shared:`;
- `test_mount_propagation_slave()` — visible bind mount must carry a `master:` peer relationship;
- `test_mount_propagation_shared()` — visible rshared bind must retain the expected shared peer group;
- `test_mount_no_leak_to_host()` — idmapped mount must be private.

Those are strong result oracles. What they do not currently distinguish is whether the modern propagation operation or its fallback produced the result.

## Harness seam

`tests/tests_utils.py` uses:

```python
def get_crun_path():
    cwd = os.getcwd()
    return os.getenv("OCI_RUNTIME") or os.path.join(cwd, "crun")
```

`run_and_get_output()` then invokes that selected path directly.

This permits a test-only launcher without product hooks or source-level fault-injection flags.

## Wrapper behavior

The retained C helper:

1. reads `REAL_CRUN`;
2. installs `PR_SET_NO_NEW_PRIVS`;
3. installs a classic seccomp BPF filter;
4. returns `ENOSYS` for syscall number `__NR_mount_setattr`;
5. allows every other syscall;
6. replaces `argv[0]` with `REAL_CRUN` and `execv()`s it.

The filter is inherited across `execve()`, so the selected crun process sees `mount_setattr()` as unavailable while retaining the older mount API.

## Helper gate executed

The wrapper was compiled locally with:

```sh
cc -Wall -Wextra -Werror -O2 \
  -o mount-setattr-deny-wrapper mount-setattr-deny-wrapper.c
```

A separate one-call probe executed:

```c
syscall(__NR_mount_setattr, -1, NULL, 0, NULL, 0);
```

Observed:

```text
unfiltered: rc=-1 errno=22 Invalid argument
filtered:   rc=-1 errno=38 Function not implemented
```

This proves the wrapper owns the intended capability discriminator before it is used as a crun test carrier.

## Exact candidate test command

On a checkout containing a built current crun and test init binary:

```sh
cc -Wall -Wextra -Werror -O2 \
  -o /tmp/mount-setattr-deny-wrapper \
  investigations/crun-propagation-fallback-stale-fd/mount-setattr-deny-wrapper.c

REAL_CRUN="$PWD/crun" \
OCI_RUNTIME=/tmp/mount-setattr-deny-wrapper \
RUN_TESTS='test_mount_propagation_private test_mount_propagation_slave test_mount_propagation_shared test_mount_no_leak_to_host' \
python3 tests/test_mounts.py
```

The helper path above assumes the Fieldwork helper has been copied into or referenced from the checkout environment. It is test machinery, not candidate source.

## Expected discriminator

### Current source

Under the filtered runtime:

- initial mount setup may use older fallbacks where newer mount operations depend on `mount_setattr()`;
- after an overmount, current `do_mount()` reopens `targetfd`;
- propagation `do_mount_setattr()` fails with injected `ENOSYS`;
- legacy propagation uses stale pre-overmount `real_target`;
- the visible mount can retain the wrong propagation state.

At least one of the propagation tests should fail if it reaches this exact path and its source/fixture provides a distinguishing visible state.

### Two-line candidate

After restoring:

```c
targetfd = fd;
get_proc_self_fd_path (target_buffer, targetfd);
real_target = target_buffer;
```

the same filtered tests should apply legacy propagation through a proc-fd pathname derived from the visible reopened mount and pass.

## Controls

### Unfiltered control

Run the same selected tests with ordinary `OCI_RUNTIME` or the real crun path directly. This proves the test environment supports the normal modern path.

### Wrapper sanity control

Run a tiny support probe through the wrapper and require `ENOSYS`, as already demonstrated in the retained local gate.

### Negative ownership control

The wrapper intentionally permits `mount(2)`. If the filtered test fails because legacy `mount(2)` itself is denied, the environment does not isolate the intended fallback boundary and the result must not be attributed to this crun defect.

### Exact-head control

Record:

```sh
git rev-parse HEAD
git diff --stat <expected-base>..HEAD
```

before treating test output as candidate evidence.

## Why external seccomp is preferable to a product fault-injection knob

A source-only environment variable or test hook would widen the product patch solely for testing. The external wrapper instead models a real compatibility class: a runtime can execute on a kernel that supports `mount_setattr()` while an outer syscall policy prevents that syscall and still permits legacy `mount(2)`.

It also tests the complete fallback stack rather than mocking only one function return inside `do_mount()`.

## Boundaries

The helper currently assumes headers expose `__NR_mount_setattr`. That is acceptable for the focused test environment; an older-header build already selects fallback at compile time and does not need seccomp to create the condition.

The filter is inherited by crun descendants. The selected propagation tests use simple payloads that do not need `mount_setattr()`, but a broader suite run should treat payload-side failures separately if a test application itself starts using that syscall.

No upstream contact is authorized or made.
