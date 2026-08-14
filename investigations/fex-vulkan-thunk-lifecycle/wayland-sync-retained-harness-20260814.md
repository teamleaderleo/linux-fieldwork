# Wayland synchronous retained-listener harness — 2026-08-14

The first Wayland listener lifetime A/B used a detached native `std::thread` to invoke the finalized FEX host trampoline. Both local and resident variants exited 139 before the required pre-close callback reached guest code, so that run was not a valid unload-lifetime discriminator.

The revised harness removes arbitrary native-thread attachment from the experiment.

## Sequence

1. Generation 1 loads the normal Wayland guest wrapper.
2. A synthetic `wl_proxy` with one `"u"` event calls the real guest `wl_proxy_add_listener` path.
3. The host thunk finalizes the real FEX host-to-guest trampoline and stores it in host-thunk static state instead of passing it to native Wayland.
4. A diagnostic thunked `fex_wl_test_trigger(41)` call is made synchronously from the guest. The host thunk invokes the retained trampoline while FEX's current thunk thread state is known to be registered.
5. Required control: guest listener prints callback value 41 and returns to the trigger call.
6. Generation 1 wrapper is `dlclose`d, its old mappings are confirmed absent, and those ranges are reserved with `MAP_FIXED_NOREPLACE` so generation 2 must move.
7. Generation 2 loads at a different guest address.
8. Generation 2 calls only `fex_wl_test_trigger(42)`. It does **not** call `wl_proxy_add_listener` again.
9. The host thunk invokes the generation-1 retained trampoline on the same FEX guest thread.

## Expected discriminator

Local wrapper-owned `"u"` unpacker:

```
pre-close trigger -> callback 41 succeeds
wrapper physically unloads
moved generation 2 trigger-only -> retained trampoline jumps to retired unpacker -> exit 139
```

Resident `"u"` unpacker:

```
pre-close trigger -> callback 41 succeeds
wrapper physically unloads
moved generation 2 trigger-only -> retained trampoline uses resident unpacker -> callback 42 succeeds
```

## Scope

Only protocol signature `"u"` is moved in the first resident candidate. If this A/B succeeds, expanding the existing finite Wayland signature dispatcher is a mechanical follow-up. The special `wl_array` signatures remain a separate 32-bit-specific check.

Workflow: `.github/workflows/wayland-sync-retained-listener.yml` on `teamleaderleo/FEX:diagnostic/wayland-resident-listener-20260814`.
