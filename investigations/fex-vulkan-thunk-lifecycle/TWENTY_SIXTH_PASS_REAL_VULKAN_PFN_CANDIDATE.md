# Twenty-sixth pass — real generated Vulkan PFN lifetime candidate

## Scope

This checkpoint moves the lifetime repair out of the synthetic thunk pair and into FEX's actual generated Vulkan guest/host thunk path.

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.
Owned-FEX branch: `ci/vulkan-pfn-lifetime-candidate-20260814`.
Carrier commit: `c1774ffc87df69f13cbf6daedfe0053fd3fa1fd3`.
Workflow run: `31771762138`.
Artifact: `9208451213`, `vulkan-pfn-lifetime-candidate-31771762138`.

The build uses FEX's generated `libvulkan-guest.so` and `libvulkan-host.so`. The minimal x86 `libX11.so.6` bootstrap exports only `XSync`, `XGetVisualInfo`, and `XDisplayString`, matching the previously isolated Vulkan guest-constructor requirement.

The guest probe then:

1. `dlopen("libvulkan.so.1")`;
2. `dlsym(vkGetInstanceProcAddr)`;
3. obtains the real `vkEnumerateInstanceVersion` PFN through GIPA;
4. calls it successfully;
5. exercises either an extra-reference close, a final close followed by stale-PFN call, or a final close + old-mapping reservation + changed-base reload.

The FEX runtime is the lock-clean revoked-H candidate with callback tombstoning and owner tracking.

## Matrix

```text
hold=0
close=139
reload=0
```

These are the intended semantics:

- `hold`: old PFN remains legal because an extra guest DSO reference keeps the thunk image mapped;
- `close`: final close revokes H, so a subsequent stale PFN remains invalid and gets a controlled synthetic guest fault;
- `reload`: a fresh guest Vulkan generation can reactivate the same stable native H against a new guest thunk target.

## Real Vulkan native PFN identity

Generation 1:

```text
PROBE acquired generation=1 ... gipa=0x7ffff7ea22b0 pfn=0x7ffff76c80f4
PROBE call where=before-close pfn=0x7ffff76c80f4
PROBE return where=before-close result=0 version=0x403113
```

FEX registers:

```text
DIAG_REVOKED_H_ACTIVATE H=0x7ffff76c80f4 T=0x7ffff7ea4400
DIAG_MULTI_ACTIVE H=0x7ffff76c80f4 T=0x7ffff7ea4400
```

So this is not merely a hand-written stand-in: the real Vulkan thunk publishes native `vkEnumerateInstanceVersion` host address `H` against a generated guest `CallHostFunction` target `T` inside `libvulkan-guest.so`.

## Extra-reference control

With a second guest `dlopen` reference held, closing the first handle does not retire the owner early:

```text
PROBE extra-ref handle=...
PROBE after-first-close maps=16
PROBE call where=after-close-with-extra-ref pfn=0x7ffff76c80f4
PROBE return where=after-close-with-extra-ref result=0 version=0x403113
```

Only the later final close triggers callback and dynamic-PFN retirement.

This is an important negative control for the pre-unmap hook: logical non-final close is harmless because no executable mapping disappears.

## Final close and revoked real Vulkan PFN

The outgoing Vulkan guest image owns five mappings. Final close removes them, and the retirement hook sees the generated thunk target inside the outgoing image:

```text
DIAG_MULTI_DROP H=0x7ffff76c80f4 T=0x7ffff7ea4400 range=0x7ffff7e75000+0x4c000
DIAG_MULTI_RETIRE H=0x7ffff76c80f4 OLD=0x7ffff7ea4400 NEW=0
DIAG_LOCKED_DEFINITION H=0x7ffff76c80f4 handler=1
DIAG_REVOKED_H_INSTALL H=0x7ffff76c80f4
DIAG_LOCKED_RETIRE H=0x7ffff76c80f4 ...
```

The same range retirement also tombstones the three real Vulkan/X11 callback trampoline records whose guest unpackers live in the Vulkan guest image:

```text
DIAG_INTEGRATED_CALLBACK_TOMBSTONE ... unpacker=0x7ffff7ea23a0 ...
DIAG_INTEGRATED_CALLBACK_TOMBSTONE ... unpacker=0x7ffff7ead050 ...
DIAG_INTEGRATED_CALLBACK_TOMBSTONE ... unpacker=0x7ffff7ea2380 ...
```

After final close:

```text
PROBE after-close maps=11 old-pfn=0x7ffff76c80f4
PROBE about-to-call-stale-pfn=0x7ffff76c80f4
PROBE call where=after-real-close pfn=0x7ffff76c80f4
DIAG_REVOKED_H_COMPILE H=0x7ffff76c80f4
```

The process exits 139 as expected for the invalid stale PFN, but the revoked-H compile marker proves FEX still recognizes the native address as a synthetic retired entry rather than decoding native ARM bytes as guest x86.

## Changed-base real Vulkan reload

After final close, the probe reserves all five former `libvulkan-guest.so` mappings:

```text
PROBE reserved-old-generation-ranges=5
```

Generation 2 is therefore forced to a different guest base.

FEX removes the revoked H definition and reactivates the same native PFN against a different generated guest target:

```text
DIAG_LOCKED_DEFINITION H=0x7ffff76c80f4 handler=1
DIAG_REVOKED_H_ACTIVATE H=0x7ffff76c80f4 T=0x7ffff7673400
DIAG_MULTI_ACTIVE H=0x7ffff76c80f4 T=0x7ffff7673400
```

The guest Vulkan image moves substantially:

```text
old GIPA = 0x7ffff7ea22b0
new GIPA = 0x7ffff76712b0
```

while the native Vulkan PFN is exactly stable:

```text
old-pfn=0x7ffff76c80f4
new-pfn=0x7ffff76c80f4
same-pfn=1
```

The fresh PFN then works:

```text
PROBE call where=after-reload-new-pfn pfn=0x7ffff76c80f4
PROBE return where=after-reload-new-pfn result=0 version=0x403113
```

Generation 2 final close then retires its new guest target and new callback trampolines cleanly.

## Conclusion

The generic lifetime mechanism is now directly demonstrated in FEX's generated Vulkan thunk path.

The real Vulkan sequence is:

```text
native Vulkan PFN H remains stable
+ generated guest CallHostFunction target T belongs to unloadable libvulkan-guest.so
+ final guest unload retires H/T and callback guest dependencies
+ stale H remains synthetic/revoked
+ changed-base reload binds the same H to a new generated T
+ real vkEnumerateInstanceVersion succeeds through the new binding
```

This materially narrows the remaining gap to the original Apple M5 teardown. The mechanism is no longer only a synthetic analogue; it is the actual generated Vulkan dynamic-PFN path.

The remaining workload-specific uncertainty is the immediate final caller in the original `vulkaninfo` exit-139 trace. The old guest thunk RIP there is known, but the retained M5 evidence did not record the native H that initiated that final transfer.

## Next discriminator

A stock-vs-candidate hosted A/B is running with byte-identical generated Vulkan guest/host thunks. It builds pristine FEX first, runs the same `hold/close/reload` probe, then incrementally rebuilds only the FEX runtime with the lifetime candidate and reruns the matrix.

That A/B will determine whether the current candidate changes real Vulkan changed-base reload from the stock stale-routing failure to successful reactivation under an otherwise identical thunk fixture.

No upstream FEX interaction was performed.