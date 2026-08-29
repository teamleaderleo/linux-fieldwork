# GNOME LocalSearch `g_file_equal()` segmentation fault

## In simple words

GNOME LocalSearch ran for about 16 hours while recursively indexing a large home
directory, then crashed with `SIGSEGV`. Ubuntu's retained crash report places the
top available frame in GLib's `g_file_equal()`, and the user service restarted
successfully.

One crash does not establish a reproducible LocalSearch defect or its trigger.
The next useful result is a controlled reduction that can distinguish ordinary
long-lived indexing, index-root removal/settings changes, and unrelated file
content. The concurrent `go.mod` MIME warnings are tracked separately and are
not assumed to have caused this crash.

## Current state

- State: `SCOPING`
- Exact working head: Linux Fieldwork base `6f52e7166bbeb05814c94ab546ec1771d6fc5d0c`
- Latest authoritative gate or artifact: Ubuntu Apport crash report for
  `/usr/libexec/localsearch-3`
- First incomplete step: reproduce in a disposable user/session or source-level
  harness without exposing private indexed filenames
- Cleanup state: the service restarted; its index scope was separately limited
  to XDG content directories and the old filesystem index was reset
- Next safe action: map the call path that can pass invalid `GFile` state to
  `g_file_equal()` and design a reduced directory/settings transition
- External-contact state: no upstream contact authorized or made

## Question

Can LocalSearch 3.11.0 reproducibly reach invalid `GFile` state during a
filesystem-root or mount/index update, and which exact lifecycle transition owns
that state?

## Source

- Project: GNOME LocalSearch and GLib/GIO
- Package version: `localsearch 3.11.0-1ubuntu1.1`
- GLib package version: `libglib2.0-0t64 2.88.0-1`
- Executable: `/usr/libexec/localsearch-3`
- Candidate source commit: none
- Local source path: not imported
- Import metadata: none

## Environment

- Distribution and release: Ubuntu 26.04.1 LTS
- Kernel and architecture: Linux `7.0.0-30-generic`, x86-64
- Host context: physical GNOME workstation (`big-red`)
- Privileges: user service plus read-only journal/Apport inspection

## Baseline behavior

The service started at login and recursively indexed `$HOME`, including a 32 GB
Projects tree and language/dependency caches. At 2026-08-29 14:14:43
Asia/Shanghai, the kernel recorded a general protection fault in
`libgio-2.0.so.0.8800.0`. systemd then reported:

```text
localsearch-3.service: Main process exited, code=dumped, status=11/SEGV
localsearch-3.service: Failed with result 'core-dump'.
```

The Ubuntu crash report records:

```text
ProblemType: Crash
Package: localsearch 3.11.0-1ubuntu1.1
SignalName: SIGSEGV
StacktraceTop:
 g_file_equal () from /usr/lib/x86_64-linux-gnu/libgio-2.0.so.0
```

systemd restarted the user service immediately. Its peak memory was 80.6 MB;
there is no evidence of system-wide memory pressure owning the crash.

## Hypotheses and discriminators

1. **Index-root lifecycle:** rapidly adding/removing a recursive root or
   resetting the filesystem database may expose stale/null `GFile` state.
2. **Mount/volume lifecycle:** a GVfs or mount appearance/disappearance may
   exercise the same comparison from a different owner.
3. **Specific indexed file:** a reduced synthetic tree may reproduce without a
   root/mount transition.
4. **Unrelated one-off corruption:** a clean disposable index and repeated
   transitions will remain stable.

Each probe needs a no-transition negative control and a clean second run after
reset. The first meaningful divergence is the call path immediately before
`g_file_equal()`, not merely another service restart.

## Reproduction plan

1. Retrieve the matching Ubuntu source and resolved upstream revision.
2. Search current and historical callers of `g_file_equal()` in LocalSearch's
   filesystem and mount/index update paths.
3. Build a disposable user-service or D-Bus session with a temporary XDG home
   and synthetic files only.
4. Compare stable-root indexing with controlled root removal, mount-like
   lifecycle, and database reset transitions.
5. Run under symbols/ASan or obtain a full backtrace only inside that synthetic
   environment.
6. Confirm cleanup: no user service, database, monitor, or temporary tree remains.

## Results

- Demonstrated: one LocalSearch 3.11.0 process crashed with `SIGSEGV`; the top
  available frame is `g_file_equal()`.
- Demonstrated: systemd recovered by restarting the user service.
- Demonstrated: broad `$HOME` indexing was unnecessary for this workstation and
  was corrected independently.
- Not demonstrated: a reproduction, faulty caller, upstream regression range,
  or causal relationship to any MIME extractor warning.

## Evidence boundary

The Apport stack is shallow because debug symbols were not present. The private
crash report and its indexed filenames are not committed. No source build,
debugger reproduction, bisection, alternate LocalSearch version, or second host
has run.

## Next step

Map current-source `g_file_equal()` callers, then construct the smallest
synthetic root/mount lifecycle probe that can both reproduce the fault and stay
stable under a negative control. Retain a negative result if the package cannot
be made to fail under bounded repeated transitions.

## Authority

Internal source research and disposable local reproduction are authorized. No
upstream issue, merge request, comment, or crash-data publication has been
authorized or made. Never publish the original crash file or private indexed
paths.
