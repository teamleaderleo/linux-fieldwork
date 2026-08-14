# Native library lifetime alignment

The guest/host lifetime asymmetry extends one layer beyond the FEX host thunk DSO.

The thunk generator emits a static native-library handle and an initializer equivalent to:

```text
static void* fexldr_ptr_<lib>_so;
fexldr_init_<lib>()
  -> dlopen(<native library>, RTLD_GLOBAL | RTLD_LAZY)
  -> resolve native symbols
```

The generator contains no emitted `dlclose()` path for that native handle.

`ThunkHandler_impl::LoadLib()` separately opens the FEX `<name>-host.so` thunk and invokes its export initializer, which calls this generated native-library initializer. FEX also has no symmetric close path for the host thunk handle.

Therefore an application `dlclose()` that physically removes only the x86 guest wrapper does not unload the native implementation behind the thunk. The process keeps:

- the FEX host thunk DSO;
- the native host library opened by generated host-loader code;
- the process-owned thunk export registry;
- any FEX host callback/trampoline state.

Only the guest wrapper text/data is reclaimed.

If the guest wrapper later loads physically again, its constructor invokes `fex:loadlib` again against this persistent host/native state. Without a symmetric unload/generation protocol, physical guest reload is not equivalent to a fresh native library generation.

This strengthens the generic `DF_1_NODELETE` interpretation: process-resident guest thunk code makes the guest implementation lifetime match the host/native lifetime FEX already implements. It is not introducing process-lifetime native-library state; that state already exists.

A future true-unload design would need to unwind all three layers together: guest wrapper, FEX host thunk/registries, and generated native-library handle/state. Retiring only guest bridge addresses is not a complete semantic unload contract.
