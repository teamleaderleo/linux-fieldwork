# Cloud Hypervisor — TDVF section semantic validation

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #590
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; none occurred

## TL;DR

The current TDVF parser verifies descriptor structure but returns section records without validating the file ranges, guest-memory ranges, or required relationships that later TDX boot code assumes.

Consumers then mix unchecked unwraps with non-exact volatile reads whose returned byte counts are ignored. A byte-valid but semantically invalid TDVF can therefore reach VMM panics (for example a missing HOB or invalid guest-memory destination) or silent partial firmware copies instead of a typed boot error.

## Explain like I'm five

The firmware file contains a little table that says “copy these bytes here.” Cloud Hypervisor checks that the table itself has the right shape, but it does not check that all the places and sizes written in the table make sense before following them.

Later code assumes they are correct. Some assumptions use `unwrap()`, and some copies do not check whether all requested bytes were actually read.

## Why care

User-selected firmware that is malformed or truncated should fail VM creation clearly. It should not panic the VMM or turn missing bytes into implicit zero-filled firmware state.

## Source boundary

`parse_tdvf_sections()` validates descriptor signature, version, declared descriptor size, and exact reading of the section-record array. It does not establish semantic ranges for each returned `TdvfSection`.

Downstream `populate_tdx_sections()` and `init_tdx_memory()` assume those ranges are safe.

Key consumers:

- BFV/CFV raw copy: `mem.read_volatile_from(...).unwrap()` with ignored returned count;
- HOB creation: `hob_offset.unwrap()`;
- PayloadParam: `mem.write_slice(...).unwrap()`;
- TDX memory init: `get_host_address_range(...).unwrap()`.

## First probes

Use byte-valid synthetic metadata:

1. descriptor with no TdHob section;
2. raw section whose `data_offset + data_size` passes EOF;
3. section destination that is not fully backed;
4. overflow-adjacent address/size values;
5. known-good TDVF control.

The first goal is not TDX execution. It is to prove the parser/consumer boundary deterministically under a panic-catching or typed-error test seam.

## Candidate boundary

Add semantic validation after section records are parsed and before VM allocation/population. Use checked arithmetic, required-section checks, type-aware source/destination rules, and exact I/O semantics.

Even after metadata validation, replace user-input-reachable unwraps with propagated errors because runtime file/memory operations remain fallible.

## Adjacent contexts

- new GUID-table metadata pointer versus deprecated pointer path;
- section types where `data_size < size` is legitimate;
- Payload sections whose bytes come from the separate payload file rather than TDVF raw data;
- unsupported versus actually malformed section combinations.

## Evidence boundary

Source-proven: structural-only parser validation, missing common semantic validation, ignored short reads, and several unwrapped downstream assumptions.

Execution pending: malformed synthetic TDVF results, exact panic/error surfaces, validator candidate, and TDX build/test gates.

## Stop condition

Narrow any subclaim if a specification-enforcing owner already proves it before this parser or if a seemingly malformed combination is valid by TDVF contract. Retain the typed-failure requirement for assumptions Cloud Hypervisor cannot safely consume.

## Authority

Internal Linux Fieldwork only. No upstream interaction is authorized or performed.
