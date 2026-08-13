Native SwiftShader control for vk_allocator_instance_probe.c

Valid create/destroy with the same non-null VkAllocationCallbacks:
- create returned success
- allocation callbacks observed: 43 allocations, 1 reallocation
- free callbacks observed: 42 total, including 10 during destroy
- exit status: 0

Mismatch simulation control:
- create used a null allocator; destroy used the callback object
- create returned success with zero allocator callback activity
- process terminated during destroy before destroy returned
- exit status: 139

The mismatch simulation is intentionally invalid on the host side and is retained only as a control model. It is not FEX runtime evidence.
