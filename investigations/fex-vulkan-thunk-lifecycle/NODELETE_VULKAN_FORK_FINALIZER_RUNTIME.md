# NODELETE Vulkan fork and process-finalizer runtime

Date: 2026-08-14

## Question

Whole-wrapper NODELETE intentionally changes guest thunk lifetime from intermediate `dlclose()` generations to process lifetime.

Two semantic questions follow:

1. does an initialized resident guest thunk remain usable across `fork()` when the child inherits FEX/thunk state?;
2. are wrapper finalizers merely delayed to process exit, or lost entirely?

## Test identity

Owned FEX branch: `diagnostic/nodelete-vulkan-fork-finalizer-20260814`.

Carrier commit: `fc5a4d1b33d9c381f41c4ef155ec7e8e13d2688d`.

Hosted ARM64 run: `31777720655`.

Artifact: `nodelete-vulkan-fork-finalizer-31777720655`.

Artifact digest:

```text
sha256:d34f124b07feef0e1795523ac0509b4830ecefa5c127afffd2f32ece709ad9e6
```

The real generated Vulkan guest wrapper is instrumented with:

```text
FIELDWORK_VULKAN_ONINIT pid=...
FIELDWORK_VULKAN_FINI pid=...
```

The actual Vulkan path is `vkGetInstanceProcAddr(NULL, "vkEnumerateInstanceVersion")` through FEX's real Vulkan host thunk and ARM64 Lavapipe.

## Sequence

Parent process:

1. loads guest Vulkan;
2. obtains and calls the dynamic native PFN;
3. logically closes the Vulkan handle;
4. calls the retained PFN after close;
5. reopens Vulkan and verifies guest GIPA and native PFN identities are unchanged;
6. closes again;
7. forks.

Child then:

1. calls the inherited retained Vulkan PFN;
2. reopens Vulkan;
3. verifies the inherited guest GIPA and native PFN identities are unchanged;
4. calls the reacquired PFN;
5. closes and returns normally from `main()`.

Parent waits for clean child exit, repeats the retained/reopen calls, and then returns normally from `main()`.

## Runtime receipt

The guest wrapper initializes once in the original parent:

```text
FIELDWORK_VULKAN_ONINIT pid=6110
INITIAL pid=6110 gipa=0x7ffff7ea2320 pfn=0x7ffff76c80f4 version=4206867
```

Pre-fork retained and reopen calls work with stable identities:

```text
PRE_FORK retained-call pid=6110 pfn=0x7ffff76c80f4 result=0 version=4206867
PRE_FORK reopen pid=6110 gipa=0x7ffff7ea2320 same_gipa=1 pfn=0x7ffff76c80f4 same_pfn=1
```

The child inherits and successfully uses the same resident generation:

```text
CHILD retained-call pid=6114 pfn=0x7ffff76c80f4 result=0 version=4206867
CHILD reopen pid=6114 gipa=0x7ffff7ea2320 same_gipa=1 pfn=0x7ffff76c80f4 same_pfn=1
CHILD_OK pid=6114 rc=0
```

No second `OnInit()` runs in the child.

The child exits normally and runs the guest wrapper finalizer:

```text
FIELDWORK_VULKAN_FINI pid=6114
```

The parent observes clean child exit and continues to use the same resident generation successfully:

```text
PARENT child-status pid=6110 status=0 exited=1 code=0
PARENT retained-call pid=6110 pfn=0x7ffff76c80f4 result=0 version=4206867
PARENT reopen pid=6110 gipa=0x7ffff7ea2320 same_gipa=1 pfn=0x7ffff76c80f4 same_pfn=1
PARENT_OK pid=6110 rc=0
NODELETE_FORK_PROBE_OK
```

The parent then runs the guest wrapper finalizer on process exit:

```text
FIELDWORK_VULKAN_FINI pid=6110
```

Explicit totals:

```text
VULKAN_ONINIT_TOTAL=1
VULKAN_FINI_TOTAL=2
exit=0
```

## Meaning

For this real generated Vulkan/FEX/glibc workload, NODELETE behaves as a process-generation lifetime contract across `fork()`:

```text
one pre-fork guest initialization
    -> inherited resident guest generation in child
    -> retained/reopened Vulkan PFN remains usable in parent and child
    -> one finalizer at child process exit
    -> one finalizer at parent process exit
```

This weakens two practical objections to the residency policy:

- it does not require rerunning guest thunk construction in the child before inherited thunk/PFN state can be used;
- it does not suppress normal process-exit finalization of the resident wrapper.

The observed behavior matches the intended process-lifetime model more closely than an intermediate unload/reload model would.

## Limits

- This covers a single-threaded fork point. It does not establish safety for `fork()` from a multithreaded guest while another thread is inside a thunk.
- It covers normal return/`exit` process teardown, not `_exit`, `execve`, fatal signals, or abnormal termination where ordinary DSO finalizers are not generally guaranteed.
- It does not prove every wrapper's process-exit finalizer is harmless; the current guest-thunk source audit remains the relevant per-wrapper check.
- The inherited FEX host-side state is part of the tested behavior; this is not a claim about arbitrary native glibc NODELETE DSOs outside FEX.

All code and CI work described here is confined to owned repositories/forks. No upstream FEX interaction occurred.
