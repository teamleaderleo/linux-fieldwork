# Cloud Hypervisor TDX Payload header read-error panic

Updated: 2026-08-13
Owning issue: #590
Reachability dependency: #654
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED — execute after #654 + Payload-destination composition resolves

## Narrow question

With the documented TDX direct-kernel configuration restored by the proven #654 validation candidate, can an ordinary user-supplied kernel path trigger a VMM panic at the TDVF `Payload` setup-header read because `read_volatile(...).unwrap()` converts a normal file read error into a panic?

## Reachable ordinary witness

On Linux, opening a directory for reading succeeds. Seeking its file descriptor also succeeds, but `read(2)` returns `EISDIR`.

That maps directly to current `TdvfSectionType::Payload` code:

```rust
payload_file
    .seek(SeekFrom::Start(0x1f1))
    .map_err(Error::LoadPayload)?;

let mut payload_header = bootparam::setup_header::default();
payload_file
    .read_volatile(&mut payload_header.as_bytes())
    .unwrap();
```

So `--kernel <directory>` can pass `File::open`, reach the Payload section after #654 restores the supported firmware+kernel mode, pass the seek, receive a volatile I/O error from the read, and panic at the unwrap.

This lane owns **read-error propagation only**. It does not yet change successful short-read semantics.

## Baseline discriminator

Production-shaped helper around the exact current operations:

- regular file with enough bytes after offset `0x1f1`: read succeeds, returned byte count is preserved;
- directory file descriptor: seek succeeds, `read_volatile()` returns an I/O error, current unwrap panics;
- normal no-panic invariant is expected red.

No TDX hardware is required for the focused seam.

## Minimum candidate

1. add typed `Error::LoadPayloadHeader(vm_memory::VolatileMemoryError)`;
2. isolate the existing seek + single `read_volatile()` into `read_tdx_payload_header()`;
3. keep seek errors under existing `Error::LoadPayload(io::Error)`;
4. map the volatile read error to `LoadPayloadHeader` and propagate with `?`;
5. preserve the existing non-exact single-read semantics and later header validation unchanged.

A later independent owner may switch the successful read to `read_exact_volatile()` after this panic owner is closed.

## Execution dependency

The eventual hosted workflow must first materialize and hash-check the immutable #654 validation repair, because exact-current baseline without that repair rejects firmware+kernel before the Payload branch is supported-reachable.

It should also keep the Payload guest-memory destination repair separate; this header read occurs before the body copy and has a different error owner.

## Gates

- exact source pin;
- immutable #654 validation layer hash;
- supported TDX firmware+kernel validation control;
- baseline regular-file header-read control;
- baseline directory-read panic witness;
- baseline no-panic invariant expected red;
- restore exact source + #654 layer;
- apply header I/O candidate;
- typed directory-read error + regular-file control;
- full VMM `tdx,kvm` tests;
- Clippy, nightly rustfmt, `git diff --check`;
- complete header-candidate-only diff and stacked product diff receipts.
