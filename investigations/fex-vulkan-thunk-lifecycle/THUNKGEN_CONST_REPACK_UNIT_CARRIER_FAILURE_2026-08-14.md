# Thunkgen const-repack unit carrier failure — 2026-08-14

## Scope

Carrier branch `ci/thunkgen-const-repack-unit-20260814`, head `756033cd13890bf10999fc88124aff7d6814316b`.

Run `31787923459`, job `94727939481`, artifact `9214270855`, artifact SHA-256 `4bbd66a1f36f05c1a7814c350355eff1f0831b88f75b1dc5ac9fdc2ca91dfe9e`.

## Result

The generic thunkgen const-pointee patch and the new `StructRepacking` regression patch both applied cleanly and passed `git diff --check`.

CMake configuration then failed before building `thunkgentest` because `BUILD_TESTING=ON` enables the repository ASM tests and the ARM64 hosted runner image did not have NASM installed:

```text
The ASM_NASM compiler identification is unknown
Didn't find assembler
CMake Error at unittests/ASM/CMakeLists.txt:1 (enable_language):
  No CMAKE_ASM_NASM_COMPILER could be found.
```

This is a carrier dependency failure. It gives no new product evidence and does not change the already-green Vulkan runtime proof for the const-pointee correction.

## Repair

The workflow dependency list was updated to install `nasm`; product and test patches remain unchanged for the rerun.
