# Callback in-flight race marker namespace fault — 2026-08-14

The first in-flight callback race carrier failed with `pin=81` and `unmap=81` because its synchronization markers used absolute `/tmp/...` paths on opposite sides of FEX's guest filesystem boundary.

The guest fixture created and polled:

```text
/tmp/fex-callback-race-arm
/tmp/fex-callback-race-entered
/tmp/fex-callback-race-release
```

through guest syscalls. The patched native FEX `ThunkHandler_impl::CallCallback` checked and created the same textual paths with host libc `access/open/write`. Those path strings refer to different backing locations when the guest runs under an explicit rootfs.

This explains the observed behavior cleanly:

- the baseline callback succeeds;
- the worker callback continues through the ordinary host-to-guest path;
- FEX never sees the guest-created arm file, so the diagnostic barrier remains inactive;
- the guest never sees a host-created entered file;
- the carrier times out its barrier poll and returns `81`.

The repair is carrier-only: use relative marker files in the fixture working directory. The workflow launches the FEX process with host cwd set to the backing rootfs fixture directory, while the guest sees that same directory as its cwd. Relative marker paths therefore resolve to the same backing files from guest code, native thunk code, and FEX host code.

No trampoline ABI or callback-lifetime mechanism changes are needed for this repair.
