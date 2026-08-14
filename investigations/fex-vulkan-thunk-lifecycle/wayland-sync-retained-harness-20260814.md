# Wayland synchronous retained-listener A/B — 2026-08-14

The first Wayland listener lifetime A/B used a detached native `std::thread` to invoke the finalized FEX host trampoline. Both local and resident variants exited 139 before the required pre-close callback reached guest code, so that run was not a valid unload-lifetime discriminator.

The revised harness removes arbitrary native-thread attachment from the experiment and is now a successful retained-registration-only A/B.

Workflow run: `31788266927`.

## Sequence

1. Generation 1 loads the normal Wayland guest wrapper.
2. A synthetic `wl_proxy` with one `"u"` event calls the real guest `wl_proxy_add_listener` path.
3. The host thunk finalizes the real FEX host-to-guest trampoline and stores it in host-thunk static state instead of passing it to native Wayland.
4. A diagnostic thunked trigger invokes that retained trampoline synchronously on the current FEX thread with value 41.
5. Required control: guest listener receives value 41 and returns successfully.
6. Generation 1 wrapper is `dlclose`d; its old mappings are confirmed absent and reserved so generation 2 must move.
7. Generation 2 loads at a different guest address.
8. Generation 2 calls only the diagnostic trigger with value 42. It does **not** call `wl_proxy_add_listener` again.
9. The host thunk invokes the generation-1 retained trampoline on the current FEX thread.

## Local arm

The pre-close callback path is valid:

```
WAYLAND_TRIGGER1_ENTER
WAYLAND_HOST_TRIGGER value=41 trampoline=...
WAYLAND_GUEST_CALLBACK count=1 value=41 data=0x12345678
WAYLAND_HOST_TRIGGER_RETURN value=41
WAYLAND_TRIGGER1_RETURN count=1 value=41
```

The wrapper then physically unloads, its old mappings are reserved, and generation 2 moves. The trigger-only retained invocation reaches the old host trampoline but exits 139 before callback 42 returns.

Result:

```
pre-close callback 41 = PASS
wrapper physically unloaded = yes
generation 2 moved = yes
listener re-registered = no
post-move retained callback = exit 139
```

## Resident `"u"` unpacker arm

The same pre-close control passes. After physical unload and moved reload:

```
WAYLAND_GEN2 add=0x7ffff7e39830 trigger=0x7ffff7e39820 moved=1
WAYLAND_TRIGGER2_ENTER retained-registration-only
WAYLAND_HOST_TRIGGER value=42 trampoline=0x7ffff7e7f000
WAYLAND_GUEST_CALLBACK count=2 value=42 data=0x12345678
WAYLAND_HOST_TRIGGER_RETURN value=42
WAYLAND_TRIGGER2_RETURN count=2 value=42
WAYLAND_SYNC_RETAINED_OK
```

Result:

```
pre-close callback 41 = PASS
wrapper physically unloaded = yes
generation 2 moved = yes
listener re-registered = no
post-move retained callback 42 = PASS / exit 0
```

## Conclusion

Wayland independently validates the same resident-executable ownership rule as CUDA, but through a different API shape:

- CUDA: generated nested `callback_member` metadata chooses a typed unpacker.
- Wayland: runtime protocol message metadata selects a callback signature through a custom dispatcher.

In both cases, the native/host-retained trampoline may outlive the unloadable wrapper, so its guest unpacker must live in process-resident guest code.

Only protocol signature `"u"` was moved for this discriminator. Expanding the resident Wayland helper across the existing finite signature switch is now a mechanical 64-bit follow-up. The special `wl_array` callback signatures still require their dedicated relocation helper, and the 32-bit path remains a separate validation target.
