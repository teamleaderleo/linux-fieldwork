# VkAllocationCallbacks probe notes

This probe isolates a callback-bearing Vulkan path that does not depend on dynamic proc-address lookup.

A valid guest supplies the same non-null VkAllocationCallbacks object to instance creation and destruction. In the reviewed FEX Vulkan thunk source at revision 71afe476751deac24adabd1adb575fd2337b6e0a, the custom instance-create path calls native Vulkan with a null allocator while instance destruction remains generic. That creates a host-side allocator-pairing asymmetry from a valid guest sequence.

Read-only external source reference: https://redirect.github.com/FEX-Emu/FEX/blob/71afe476751deac24adabd1adb575fd2337b6e0a/ThunkLibs/libvulkan/Host.cpp

The native SwiftShader valid control observed 43 allocations, 1 reallocation, and 42 frees, including 10 frees during instance destruction, and exited successfully.

The optional mismatch-simulation mode creates natively with a null allocator and destroys with the callback object. That host-side sequence is intentionally Vulkan-invalid. It returned successfully from creation with zero allocator callback activity and terminated during destruction with status 139. This is retained only as a control model and is not FEX runtime evidence.

On x86-64 the allocation, reallocation, and free callback stubs carry the same raw cross-ISA entry discriminator used by the debug-report probe. The target FEX proof should run the normal valid guest mode only. A failure after the destroy-enter marker and before destroy-return, with the fault location at a printed callback address, would support raw allocator callback escape during destruction.

Keep this probe separate from the dynamic debug-report/debug-utils lookup finding and from the guest Vulkan thunk unload/lifecycle finding. FEX upstream remained read-only.
