# Cloud Hypervisor TDX Payload bzImage setup-size validation

Updated: 2026-08-13
Owning issue: #590
Reachability dependency: #654
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Final tested Fieldwork head: `48f49c1328a9c93d7e7300852ebe81ee2c3bac2a`
External-contact state: false; upstream remains read-only
State: **PROVEN AFTER #654 REACHABILITY LAYER**

## Result

After the proven #654 validation repair restores the documented TDX direct-kernel path, exact-current Cloud Hypervisor accepts a bzImage-shaped payload whose own setup header requires a setup area larger than the entire file.

A 530-byte file containing every field the TDX-specific path checks (`HdrS`, protocol 2.00, `LOAD_HIGH`) is accepted by those checks even though `setup_sects=0` means the Linux protocol default setup area is 2,560 bytes. Cloud Hypervisor's pinned ordinary `linux-loader 0.14.0` rejects the same file/setup relationship as `Bzimage(Underflow)`.

The minimum TDX-side candidate reuses the Linux protocol's effective `setup_sects` rule and rejects `payload_size < (setup_sectors + 1) * 512` before copying the kernel or publishing payload information.

## Independent protocol/loader basis

Linux `Documentation/arch/x86/boot.rst` states:

- the setup header begins at file offset `0x1f1`;
- `setup_sects` is the number of setup sectors;
- `setup_sects == 0` means 4 for compatibility;
- the real-mode image consists of one boot sector plus the setup sectors.

Cloud Hypervisor pins `linux-loader = 0.14.0`, exact source `rust-vmm/linux-loader@f950496af619300acc40181bb505e6c64c22e4d9`. Its ordinary `BzImage::load()` performs the same non-exact setup-header read as the TDX path, but then computes the setup size and rejects a file shorter than that area via checked subtraction (`Bzimage(Underflow)`).

This is why the candidate is a structural setup-area check rather than a blanket exact read of the newest 123-byte Rust setup-header struct. The Linux header is versioned and later fields were added across protocol revisions.

## Reachability layer

The workflows first materialize the immutable #654 TDX payload-validation repair:

- materializer carrier `921b7ecd5ee25889000d1fcaabbcc578a4cbbc69`
- expected/reverified diff SHA-256 `0af9d875fd2b82099fe15f7f6a910d9500293990846bda6d677da1ea16b0da5e`

That restores the exact-current documented `firmware + kernel` TDX mode before exercising the Payload consumer.

## Baseline execution

The first workflow (`31666587678`) was harness-only red at a brittle Cargo.toml grep; no product probe ran.

Authoritative baseline run:

- run `31666706578`
- job `94342724888`
- tested carrier `9493544360e2b9da6016cb847e58f880ce1164fd`
- artifact `9168215268`

Fixture:

```text
file length = 0x212 (530 bytes)
setup_sects @ 0x1f1 = 0  -> effective 4
HdrS        @ 0x202 = valid
version     @ 0x206 = 0x0200
loadflags   @ 0x211 = LOAD_HIGH
required setup area = (4 + 1) * 512 = 0xa00 (2560 bytes)
```

Baseline evidence:

```text
TDX_PAYLOAD_SETUP_BASELINE payload_size=0x212 setup_size=0xa00 accepted=true
TDX_PAYLOAD_SETUP_BASELINE_INVARIANT_RC=101
```

Pinned ordinary loader negative control:

```text
TDX_PAYLOAD_SETUP_CONTROL linux_loader_result=Bzimage(Underflow)
```

Valid control with file length exactly `0xa00` remained accepted.

The v2 candidate focused check and full VMM suite passed. Its only red gate was a regression-test Clippy `field-reassign-with-default` lint; product code was not implicated. The test-only construction syntax was then cleaned.

## Candidate

Product semantics:

```rust
fn validate_tdx_payload_setup_size(
    payload_size: u64,
    payload_header: &bootparam::setup_header,
) -> Result<()> {
    let setup_sects = payload_header.setup_sects;
    let setup_sectors = if setup_sects == 0 {
        4
    } else {
        u64::from(setup_sects)
    };
    let setup_size = (setup_sectors + 1) * 512;
    if payload_size < setup_size {
        return Err(Error::InvalidPayloadSetupSize {
            payload_size,
            setup_size,
        });
    }
    Ok(())
}
```

It is called only after the existing TDX magic/version/`LOAD_HIGH` checks and before payload rewind/copy.

Focused candidate:

```text
TDX_PAYLOAD_SETUP_CANDIDATE truncated_result=InvalidPayloadSetupSize { payload_size: 530, setup_size: 2560 }
TDX_PAYLOAD_SETUP_CANDIDATE default_setup_control=ok
TDX_PAYLOAD_SETUP_CANDIDATE explicit_setup_control=ok
```

## Final immutable receipt

Final hosted run:

- run `31667024677`
- job `94343705910`
- tested Fieldwork head `48f49c1328a9c93d7e7300852ebe81ee2c3bac2a`
- artifact `9168318302`
- artifact digest `sha256:05dc86fb611df367b21c51267917c6b214c71af0e8fa336530792b422e0f2aa6`
- bundle `tdx-payload-setup-size-final.zip`
- final setup-size candidate-only diff SHA-256 `065d1ae825202e08b2861669397652c2867f95c05debd6650bf68d28db5bd5c2`
- stacked #654 + setup-size diff SHA-256 `aefa94fcb8db6543e4e8ec586e6344e3f5d1e96a03ffeb527c23a4d36a33ed50`

Stacked product stat:

```text
3 files changed, 88 insertions(+), 8 deletions(-)
```

Final gates:

```text
focused reachability + setup-size candidate: success
full VMM tdx,kvm: 109 passed, 0 failed, 2 intentionally ignored #654 baseline witnesses
Clippy: success
nightly rustfmt: success
git diff --check: success
```

Complete final `vmm/src/vm.rs` candidate-only diff was reviewed. Product change is one typed error, one setup-size helper, and one call-site check; remaining changes are the focused regression test.

## Disposition

**PROVEN AFTER #654 REACHABILITY LAYER.** The TDX-specific Payload path accepts a kernel file shorter than the setup area declared by its own bzImage header, unlike Cloud Hypervisor's pinned ordinary bzImage loader. The minimum structural setup-size guard is validated.

## Next frontier

A separate high-priority spec mismatch remains: TD-Shim metadata explicitly permits an embedded `Payload` whose `RawDataSize` is nonzero, and says the VMM shall load corresponding components from the firmware image. Exact-current Cloud Hypervisor performs `Payload` work only when a separate `self.kernel` file exists, so firmware-only TDX appears to skip a spec-valid embedded payload entirely. Keep that owner separate from external-kernel validation and copy handling.
