# Cloud Hypervisor TDX Payload header read-error panic

Updated: 2026-08-13
Owning issue: #590
Reachability dependency: #654
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Final tested Fieldwork head: `1a8c97cb89c0acc6fce6c0342ee75a662080456d`
External-contact state: false; upstream remains read-only
State: **PROVEN AFTER #654 REACHABILITY LAYER**

## Result

After the proven #654 validation repair restores Cloud Hypervisor's documented TDX `firmware + kernel` mode, an ordinary user-supplied kernel path can trigger a VMM panic at the TDVF `Payload` setup-header read.

On Linux, `File::open()` succeeds for a directory and seeking its descriptor succeeds, but reading it returns `EISDIR`. Exact-current TDX code converts that ordinary volatile I/O error into a panic with `.unwrap()`.

The minimum candidate preserves the existing seek and successful non-exact header-read semantics but maps volatile read errors to a typed `LoadPayloadHeader(VolatileMemoryError)` and propagates them with `?`.

Baseline, candidate, full VMM, Clippy, formatting, and diff-hygiene gates are complete.

## Reachability

This owner is intentionally stacked on the immutable #654 TDX payload-validation repair:

- materializer carrier `921b7ecd5ee25889000d1fcaabbcc578a4cbbc69`
- reverified #654 diff SHA-256 `0af9d875fd2b82099fe15f7f6a910d9500293990846bda6d677da1ea16b0da5e`

The workflow first proves the restored documented TDX firmware+kernel configuration validates. No Payload-destination repair is stacked here because header I/O occurs earlier and has a distinct first-failing owner.

## Exact source owner

Current `TdvfSectionType::Payload` code performs:

```rust
payload_file
    .seek(SeekFrom::Start(0x1f1))
    .map_err(Error::LoadPayload)?;

let mut payload_header = bootparam::setup_header::default();
payload_file
    .read_volatile(&mut payload_header.as_bytes())
    .unwrap();
```

The seek already propagates a normal `io::Error`; only the volatile read is unwrapped.

## Baseline execution

Baseline/candidate run:

- run `31665957881`
- job `94340452045`
- tested carrier `0782f23b4a0d7594945f7be1e360bf9be38afaad`
- artifact `9167958847`
- artifact digest `sha256:e9a73f6d3189a1ca4592787870a4448fce1b5719a2892802aa5db3b4d14e6432`

Baseline regular-file control succeeded.

Directory witness:

```text
called `Result::unwrap()` on an `Err` value:
IOError(Os { code: 21, kind: IsADirectory, message: "Is a directory" })
TDX_PAYLOAD_HEADER_BASELINE panicked=true
```

Normal no-panic invariant:

```text
TDX_PAYLOAD_HEADER_BASELINE_INVARIANT_RC=101
TDX_PAYLOAD_HEADER_INVARIANT panicked=true
```

The first candidate already passed focused and full VMM testing. Its only red gate was a Clippy `absolute_paths` lint in the candidate regression test's spelling of `std::mem::size_of`; product code was not implicated.

That test-only spelling was cleaned before the final run.

## Minimum candidate

Product semantics:

1. add `Error::LoadPayloadHeader(vm_memory::VolatileMemoryError)`;
2. add `read_tdx_payload_header()` that preserves the existing seek mapping to `LoadPayload`;
3. preserve the existing single `read_volatile()` behavior for successful reads;
4. map only its error to `LoadPayloadHeader`;
5. replace the production seek/read unwrap block with `Self::read_tdx_payload_header(payload_file)?`.

Final focused result:

```text
TDX_PAYLOAD_HEADER_CANDIDATE directory_result=LoadPayloadHeader(
    IOError(Os { code: 21, kind: IsADirectory, message: "Is a directory" })
)
TDX_PAYLOAD_HEADER_CANDIDATE regular_file_read=ok
```

## Final immutable receipt

Final hosted run:

- run `31666242005`
- job `94341287293`
- tested Fieldwork head `1a8c97cb89c0acc6fce6c0342ee75a662080456d`
- artifact `9168051027`
- artifact digest `sha256:10b6a93db16c0f8ba901f2c350ca0318d3a5f811e61473483f69b8f1ccd4e0d8`
- final header candidate-only diff SHA-256 `dda5a92f3247aa27637e80a554ef59122a5876f797ac6e6af029d3952f67aa1e`
- stacked #654 + header-candidate diff SHA-256 `ae2006eca15bc09628932d8a680124e7586ee3d6b2b4f54d9c06aa7a09abf6c0`

The only change from the first candidate materializer is the test-only `size_of` import cleanup; product semantics are unchanged.

Final gates:

```text
focused reachability + header error: success
full VMM tdx,kvm: 109 passed, 0 failed, 2 intentionally ignored #654 baseline witnesses
Clippy: success
nightly rustfmt: success
git diff --check: success
```

Complete final `vmm/src/vm.rs` candidate diff was reviewed. Product change is one typed error, one helper, and one call-site replacement; remaining changes are the focused regression test.

## Disposition

**PROVEN AFTER #654 REACHABILITY LAYER.** A supported TDX direct-kernel configuration can reach a normal payload setup-header read error, and exact-current source panics. The minimum typed error-propagation repair is validated.

## Short-read stop condition

Do **not** replace the setup-header read with a blanket full-struct exact read. Linux's x86 boot protocol header is versioned; later fields were added across protocol revisions, and the `jump` field can describe header size. Cloud Hypervisor's pinned normal `linux-loader` bzImage path also performs a non-exact struct read.

The next separate owner is structural instead: the pinned normal bzImage loader uses `setup_sects` to require that the file contain its declared/default setup area and returns `Underflow` when it does not. The TDX path currently lacks that file-size check.
