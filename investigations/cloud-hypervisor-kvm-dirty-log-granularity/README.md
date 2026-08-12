# Cloud Hypervisor — KVM dirty-log bitmap granularity

Updated: 2026-08-12
State: COMPLETE — SOURCE-CONTRACT AUDIT VERIFIED
Owning issue: #617
Canonical Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Canonical Linux source: `f5bbbfec59b4e2fb7520a91de3df8a6174325d6a`
External-contact state: `false; none occurred`

## TL;DR

The KVM half of issue #617 is verified independently from primary source.

In the current Cloud Hypervisor path, each bit returned by `KVM_GET_DIRTY_LOG` represents one KVM guest frame number, and KVM defines that guest frame number with the running kernel's compiled `PAGE_SHIFT`. On AArch64 kernels built with 16 KiB or 64 KiB base pages, one KVM dirty bit therefore covers 16 KiB or 64 KiB of guest physical memory.

Exact `kvm-ioctls 0.25.0` does **zero bit-index normalization to 4 KiB**. It reads `_SC_PAGESIZE` only to allocate a correctly sized userspace vector, points `KVM_GET_DIRTY_LOG` directly at that vector, and returns it unchanged. Exact `vm-memory 0.18.0` also uses `_SC_PAGE_SIZE` for ordinary `AtomicBitmap` construction, so the KVM bitmap and VMM bitmap being ORed by Cloud Hypervisor use the same host-base-page unit.

`MemoryManager::dirty_log()` then decodes those combined bit positions with a hardcoded `4096`. That is the first unit mismatch in the KVM path.

MSHV carries a separate contract: Cloud Hypervisor shifts GPAs by 12 and exact `mshv-ioctls 0.6.9` uses Hyper-V's fixed `HV_PAGE_SIZE`, whose header definition is `HV_HYP_PAGE_SHIFT = 12`. MSHV therefore legitimately remains 4 KiB-granular.

## Explain like I'm five

A dirty bitmap is a row of yes/no marks. Each mark says “send this chunk of guest memory again.”

On a 16 KiB KVM host, mark 1 means the second 16 KiB chunk:

```text
slot base = 0x4000_0000
KVM bit 1 = 0x4000_4000 .. 0x4000_7fff
```

Cloud Hypervisor currently reads that same mark as the second 4 KiB chunk:

```text
current decode = 0x4000_1000 .. 0x4000_1fff
```

The mark survives every layer unchanged. The wrong byte unit appears when Cloud Hypervisor converts the mark into a migration memory range.

## Why care

Live migration relies on dirty logging to resend guest RAM changed after the earlier memory copy. Decoding a dirty bit with a smaller, wrong page unit can resend the wrong GPA and too few bytes. The destination can therefore retain stale guest memory while migration otherwise completes normally.

The repair also needs backend awareness. KVM uses the Linux host kernel's base-page granule; MSHV uses the Hyper-V 4 KiB page granule.

## Current state

- State: `COMPLETE` for the bounded kernel/API contract audit
- Exact working head: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
- Latest authoritative evidence: exact Linux, Cloud Hypervisor, `kvm-ioctls`, `vm-memory`, and `mshv-ioctls` source listed below
- First incomplete step: none inside the normalization question; real 16 KiB/64 KiB migration execution belongs to candidate validation
- Cleanup state: no external system or upstream repository changed
- Next safe action: make dirty-log granularity an explicit backend contract and add synthetic 16 KiB/64 KiB conversion tests before hardware migration validation
- External-contact state: `false; none occurred`

## Question

Does each KVM dirty-log bitmap bit received by current Cloud Hypervisor still represent one host-kernel KVM base page, or does Linux, `kvm-ioctls`, or another layer expand/normalize the bitmap into 4 KiB bit positions before `MemoryManager::dirty_log()` consumes it?

## Source boundary

### Cloud Hypervisor

Resolved head: `1af93ac7035cda77cd87b0c18b1134ebb0928052`

Relevant files:

- [`vmm/src/memory_manager.rs`](https://github.com/cloud-hypervisor/cloud-hypervisor/blob/1af93ac7035cda77cd87b0c18b1134ebb0928052/vmm/src/memory_manager.rs)
- [`hypervisor/src/kvm/mod.rs`](https://github.com/cloud-hypervisor/cloud-hypervisor/blob/1af93ac7035cda77cd87b0c18b1134ebb0928052/hypervisor/src/kvm/mod.rs)
- [`hypervisor/src/mshv/mod.rs`](https://github.com/cloud-hypervisor/cloud-hypervisor/blob/1af93ac7035cda77cd87b0c18b1134ebb0928052/hypervisor/src/mshv/mod.rs)
- [`vm-migration/src/protocol.rs`](https://github.com/cloud-hypervisor/cloud-hypervisor/blob/1af93ac7035cda77cd87b0c18b1134ebb0928052/vm-migration/src/protocol.rs)
- [`Cargo.lock`](https://github.com/cloud-hypervisor/cloud-hypervisor/blob/1af93ac7035cda77cd87b0c18b1134ebb0928052/Cargo.lock)

Pinned dependencies from that lockfile:

```text
kvm-ioctls  = 0.25.0
vm-memory   = 0.18.0
mshv-ioctls = 0.6.9
mshv-bindings = 0.6.9
```

### Linux KVM

Resolved source: `torvalds/linux@f5bbbfec59b4e2fb7520a91de3df8a6174325d6a`

Relevant files:

- [`virt/kvm/kvm_main.c`](https://github.com/torvalds/linux/blob/f5bbbfec59b4e2fb7520a91de3df8a6174325d6a/virt/kvm/kvm_main.c)
- [`include/linux/kvm_host.h`](https://github.com/torvalds/linux/blob/f5bbbfec59b4e2fb7520a91de3df8a6174325d6a/include/linux/kvm_host.h)
- [`Documentation/virt/kvm/api.rst`](https://github.com/torvalds/linux/blob/f5bbbfec59b4e2fb7520a91de3df8a6174325d6a/Documentation/virt/kvm/api.rst)
- [`arch/arm64/Kconfig`](https://github.com/torvalds/linux/blob/f5bbbfec59b4e2fb7520a91de3df8a6174325d6a/arch/arm64/Kconfig)
- [`arch/Kconfig`](https://github.com/torvalds/linux/blob/f5bbbfec59b4e2fb7520a91de3df8a6174325d6a/arch/Kconfig)
- [`arch/arm64/kvm/mmu.c`](https://github.com/torvalds/linux/blob/f5bbbfec59b4e2fb7520a91de3df8a6174325d6a/arch/arm64/kvm/mmu.c)

### Exact Rust dependency source

- `kvm-ioctls 0.25.0`: [`rust-vmm/kvm@b4c9ed8d.../kvm-ioctls/src/ioctls/vm.rs`](https://github.com/rust-vmm/kvm/blob/b4c9ed8df95a9e10a68f50f5ef5e7d04108759ba/kvm-ioctls/src/ioctls/vm.rs)
- `vm-memory 0.18.0`: [`rust-vmm/vm-memory@b6404d24.../atomic_bitmap.rs`](https://github.com/rust-vmm/vm-memory/blob/b6404d240d639a231abcd2b2db5a4b79ca43059c/src/bitmap/backend/atomic_bitmap.rs)
- `mshv-ioctls 0.6.9`: [`rust-vmm/mshv@b7f7960f.../mshv-ioctls/src/ioctls/vm.rs`](https://github.com/rust-vmm/mshv/blob/b7f7960f0c35d50e4d61b9e6a541a73b07312a28/mshv-ioctls/src/ioctls/vm.rs)
- Hyper-V page definition: [`rust-vmm/mshv@b7f7960f.../hv-headers/hvgdk_mini.h`](https://github.com/rust-vmm/mshv/blob/b7f7960f0c35d50e4d61b9e6a541a73b07312a28/hv-headers/hvgdk_mini.h)

## Contract trace

Let `H = 1 << PAGE_SHIFT` for the running KVM host kernel and let a Cloud Hypervisor guest RAM mapping have base GPA `B` and byte length `L`.

### 1. Guest memory length → KVM memslot pages

Linux validates the KVM userspace memory region against `PAGE_SIZE`, then computes:

```c
base_gfn = mem->guest_phys_addr >> PAGE_SHIFT;
npages   = mem->memory_size >> PAGE_SHIFT;
```

So the memslot contains `L / H` GFNs. The kernel's generic `PAGE_SHIFT` configuration maps 4 KiB to 12, 16 KiB to 14, and 64 KiB to 16. AArch64 explicitly supports all three base-page configurations.

### 2. Memslot page → bitmap bit

KVM sizes its dirty bitmap from `memslot->npages`:

```c
ALIGN(memslot->npages, BITS_PER_LONG) / 8
```

When a GFN is marked dirty, KVM computes:

```c
rel_gfn = gfn - memslot->base_gfn;
set_bit_le(rel_gfn, memslot->dirty_bitmap);
```

Therefore bitmap bit `i` means the GFN at `base_gfn + i`, which corresponds to guest bytes:

```text
[B + i*H, B + (i+1)*H)
```

`KVM_GET_DIRTY_LOG` copies this bitmap to userspace.

### 3. Kernel bitmap → `kvm-ioctls 0.25.0`

Exact `kvm-ioctls` does this before the ioctl:

```rust
page_size = sysconf(_SC_PAGESIZE)
bitmap_size = memory_size.div_ceil(page_size * 64)
bitmap = vec![0u64; bitmap_size]
dirty_bitmap = bitmap.as_mut_ptr()
KVM_GET_DIRTY_LOG(...)
return bitmap
```

The `page_size * 64` multiplication is buffer sizing: one `u64` stores 64 KVM dirty bits. There is no loop that expands one host-page bit into multiple 4 KiB bits, no shift from host `PAGE_SHIFT` to 12, and no post-ioctl rewrite. The vector filled by the kernel is the vector returned to Cloud Hypervisor.

This directly falsifies the hidden-normalization alternative.

### 4. VMM writes → `vm-memory 0.18.0 AtomicBitmap`

Cloud Hypervisor's ordinary guest memory type uses `AtomicBitmap`.

Exact `AtomicBitmap::with_len()` on Unix reads:

```rust
libc::sysconf(libc::_SC_PAGE_SIZE)
```

and constructs `AtomicBitmap::new(len, page_size)`. Address tracking converts bytes to bit index with `addr / page_size`, while `get_and_reset()` returns the underlying `u64` words.

On KVM, both inputs to Cloud Hypervisor's OR therefore carry the same unit `H`:

```text
KVM bit i       = host base page i
AtomicBitmap i  = host base page i
```

### 5. Combined bitmap → Cloud Hypervisor range

`MemoryManager::dirty_log()` currently does:

```rust
vm_dirty_bitmap = self.vm.get_dirty_log(...)
vmm_dirty_bitmap = region.bitmap().get_and_reset()

dirty_bitmap = zip(vm_dirty_bitmap, vmm_dirty_bitmap).map(|(x, y)| x | y)
MemoryRangeTable::from_dirty_bitmap(dirty_bitmap, r.gpa, 4096)
```

`MemoryRangeTable` converts a dirty run `[start, end)` into:

```text
gpa    = start_addr + start * page_size
length = (end - start) * page_size
```

The hardcoded `4096` therefore reinterprets KVM/VMM bit index `i` as `B + i*4096` even when its producer contract is `B + i*H`.

There is no later multiplication or page-shift conversion that restores the original KVM unit.

## AArch64 base-page discriminator

For a 1 MiB slot:

| Host base page | KVM/VMM page bits | `u64` words | Meaning of bit 1 | Current decode of bit 1 |
| --- | ---: | ---: | ---: | ---: |
| 4 KiB | 256 | 4 | `+0x1000` | `+0x1000` |
| 16 KiB | 64 | 1 | `+0x4000` | `+0x1000` |
| 64 KiB | 16 | 1 | `+0x10000` | `+0x1000` |

Tiny arithmetic probe executed during the audit:

```python
for page_size in (4096, 16384, 65536):
    length = 1 << 20
    pages = length // page_size
    words = (pages + 63) // 64
    print(page_size, pages, words, hex(page_size), hex(4096))
```

Observed:

```text
4096  256 4 0x1000  0x1000
16384  64 1 0x4000  0x1000
65536  16 1 0x10000 0x1000
```

The 16 KiB and 64 KiB cases contain no extra 4 KiB bit positions for Cloud Hypervisor to consume. Their bitmap lengths already reflect host-base-page counting.

## MSHV contract

MSHV follows a different unit all the way through.

Cloud Hypervisor declares:

```rust
pub const PAGE_SHIFT: usize = 12;
```

and calls dirty logging with:

```rust
base_gpa >> PAGE_SHIFT
```

Exact `mshv-ioctls 0.6.9` accepts `base_pfn`, computes total pages and bitmap allocation using `HV_PAGE_SIZE`, and asks for GPA-page-access state in those PFNs. The matching Hyper-V header defines:

```c
#define HV_HYP_PAGE_SHIFT 12
#define HV_HYP_PAGE_SIZE  BIT(HV_HYP_PAGE_SHIFT)
```

So one MSHV dirty bit is 4096 bytes by backend contract.

A repair should preserve this backend distinction:

```text
KVM  dirty bit = running Linux KVM host base PAGE_SIZE
MSHV dirty bit = Hyper-V HV_HYP_PAGE_SIZE = 4096
```

## Violated contract

The violated contract is the consumer's interpretation of an untyped bitmap.

For KVM, producers hand `MemoryManager` bit position `i` meaning:

```text
GPA = slot_base + i * host_kernel_page_size
length = host_kernel_page_size
```

`MemoryManager` currently consumes the same bit as:

```text
GPA = slot_base + i * 4096
length = 4096
```

The correct granule belongs to the backend result or backend API. A typed dirty-log result carrying both bitmap and granule would make this harder to misuse; a smaller backend `dirty_log_page_size()` contract can also repair the current call path if the bitmap/granule pairing remains explicit.

## Adjacent compatibility question

`AtomicBitmap::with_len()` follows the Linux userspace host page size, while MSHV follows Hyper-V's fixed 4 KiB page size. On the common x86_64 Linux case those values coincide.

If Cloud Hypervisor MSHV dirty logging is supported on an AArch64 Linux host with a 16 KiB or 64 KiB base page, the VMM `AtomicBitmap` and MSHV bitmap would carry different units before the current word-wise OR. That is a separate backend-compatibility question and should be answered before claiming a global host-page-size replacement is correct for every backend.

It does not weaken the KVM conclusion.

## Evidence boundary

Established from exact source:

- Linux KVM memslot `npages` uses the compiled `PAGE_SHIFT`;
- KVM dirty bit index is relative GFN and bitmap allocation is based on `npages`;
- AArch64 Linux supports 4 KiB, 16 KiB, and 64 KiB kernel base pages;
- `kvm-ioctls 0.25.0` allocates using `_SC_PAGESIZE` and returns the kernel-filled bitmap unchanged;
- `vm-memory 0.18.0 AtomicBitmap` uses `_SC_PAGE_SIZE` and returns its bitmap words unchanged;
- current Cloud Hypervisor ORs KVM and VMM words directly and decodes them with `4096`;
- MSHV uses the separate fixed Hyper-V 4 KiB page contract.

Outside this bounded audit:

- no AArch64 16 KiB/64 KiB KVM live migration was executed;
- no guest-visible stale-memory demonstration was run;
- no Cloud Hypervisor product patch was created here;
- MSHV-on-non-4KiB-host compatibility remains a separate question.

Those items affect fix validation and backend breadth. They do not reopen the source-contract question unless a new layer is introduced between these exact producers and `MemoryManager`.

## Next step

For the KVM fix:

1. carry dirty-log granularity explicitly from the hypervisor backend;
2. return the Linux host base page size for KVM;
3. return 4096 for MSHV;
4. use that granule in `MemoryRangeTable::from_dirty_bitmap()`;
5. validate bitmap-unit compatibility before OR-ing producer bitmaps;
6. add synthetic 16 KiB and 64 KiB bit-to-GPA tests plus the existing 4 KiB control;
7. validate the candidate on a real AArch64 non-4KiB KVM migration before making an end-to-end preservation claim.

## Disposition

**VERIFIED** — the KVM dirty-log bitmap reaches Cloud Hypervisor in host-kernel base-page units. No 4 KiB normalization exists in the exact current path. The hardcoded `4096` in `MemoryManager::dirty_log()` violates that KVM bit-to-GPA contract. MSHV legitimately remains 4 KiB-granular under its Hyper-V contract.

## Authority

No upstream issue, email, pull request, patch submission, comment, review, reaction, or other third-party interaction was authorized or created during this audit. All work stayed within Linux Fieldwork and read-only upstream source inspection.
