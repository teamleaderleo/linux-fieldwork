# Cloud Hypervisor TDX Payload bzImage setup-size validation

Updated: 2026-08-13
Owning issue: #590
Reachability dependency: #654
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED — do not execute until current Payload-header-I/O lane releases the runner slot

## Narrow question

After the proven #654 validation repair restores the documented TDX direct-kernel path, can the TDX `Payload` consumer accept a kernel file that has the checked bzImage magic/version/load flag but is shorter than the setup area declared by its own Linux setup header?

This is not a request to read the entire newest 123-byte Rust `setup_header` exactly. The Linux boot header is versioned, and later fields were added across protocol revisions. Full-struct exact-read would be unnecessarily strict.

## Independent loader/protocol basis

Linux `Documentation/arch/x86/boot.rst` says:

- setup header begins at file offset `0x1f1`;
- `setup_sects` is one byte at `0x1f1`;
- if `setup_sects == 0`, its real value is 4;
- the real-mode image consists of one boot sector plus `setup_sects` setup sectors.

Cloud Hypervisor pins `linux-loader = 0.14.0` (`f950496af619300acc40181bb505e6c64c22e4d9`). Its ordinary `BzImage::load()` reads the same setup header non-exactly, then computes:

```text
setup_size = (effective_setup_sects + 1) * 512
kernel_size = file_size.checked_sub(setup_size)
```

and returns `Underflow` if the file is shorter than the setup area.

The TDX `Payload` path performs the magic/version/LOAD_HIGH checks but does not perform that structural file-size check before treating the file as `PayloadImageType::BzImage` and copying the whole file to guest memory.

## Baseline discriminator

Build an ordinary 530-byte file ending immediately after `loadflags`:

```text
file length: 0x212
setup_sects @ 0x1f1: 0     # protocol default = 4
HdrS magic   @ 0x202: valid
version      @ 0x206: 0x0200
loadflags    @ 0x211: LOAD_HIGH
```

Current TDX header checks should accept those fields. But the protocol-defined setup area is:

```text
(4 + 1) * 512 = 0xa00 = 2560 bytes
```

which is larger than the entire file.

The ordinary pinned `linux-loader::BzImage::load()` should reject the same structural relationship as `Underflow`.

Control: a file at least `0xa00` bytes long with the same header fields.

## Minimum candidate

After the existing TDX header magic/version/loadflags checks, compute effective `setup_sects` using the Linux protocol's `0 -> 4` compatibility rule and reject `payload_size < (setup_sects + 1) * 512` with a typed VMM payload-size error before guest copy/HOB publication.

Do not change successful header-read semantics, Payload destination propagation, or generic bzImage loading.

## Gates when executed

- exact source pin;
- immutable #654 reachability layer hash;
- documented TDX firmware+kernel validation control;
- truncated TDX bzImage baseline acceptance witness;
- pinned `linux-loader` underflow negative control for the same setup/file relationship;
- normal expected-red structural invariant;
- typed candidate rejection + valid-size control;
- full VMM `tdx,kvm` library tests;
- Clippy, nightly rustfmt, `git diff --check`;
- complete candidate-only and stacked diff receipts.
