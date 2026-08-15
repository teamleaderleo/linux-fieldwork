# Bus stack v2 — preserve in-flight device lifetime

Updated: 2026-08-15

Exact upstream base: `69d4c0a82ef15b2660906013bd87ae32668e7998`
External-contact state: false

## Why v2 exists

A fresh self-review of the first clean Bus stack found a fidelity gap in `Bus::update_range()`.

Historical/current baseline obtains the device through `resolve()`, which upgrades the stored weak reference and therefore holds a strong `Arc<dyn BusDeviceSync>` for the duration of the move.

The first clean stack (`2edcf22f0bd35beff06ab2b4e132cf240e54d2f9`) instead cloned the stored `Weak`, checked `upgrade().is_none()`, discarded that temporary strong reference, and later reinserted the same `Weak`.

The post-return Bus contract still stores only a weak reference, but the first candidate no longer preserved the baseline's **in-flight** lifetime guarantee if the caller's last external `Arc` disappeared concurrently with `update_range()`.

This is a candidate-fidelity defect rather than a new upstream bug. The corrected implementation preserves the old lifetime while retaining the one-lock atomic range update:

```rust
let device = devices
    .get(&old_range)
    .and_then(Weak::upgrade)
    .ok_or(Error::MissingAddressRange)?;

// validate NEW while the strong Arc stays alive

 devices.remove(&old_range);
 debug_assert!(
     devices
         .insert(new_range, Arc::downgrade(&device))
         .is_none()
 );
```

## Deterministic lifetime discriminator

The authoritative research workflow adds a **test-only** barrier immediately after `update_range()` has obtained its device reference.

Sequence:

```text
caller owns last external Arc
Bus stores Weak
update_range starts and obtains device
-> pause
caller drops last external Arc
-> device must still be alive while update_range is in flight
resume move
update_range returns
-> only Bus Weak remains, so device may now drop
```

The test asserts `Weak::upgrade().is_some()` during the pause and `Weak::upgrade().is_none()` after `update_range()` returns.

The barrier and test hook are workflow-only. They are removed before the product candidate is committed.

## Authoritative execution

Research branch:

`teamleaderleo/cloud-hypervisor:research/ch-bus-r677-r678-r679-v2`

Workflow run/job:

`31899954631` / `95049007724`

Artifact:

`9250804219`

Artifact digest:

`sha256:80b27e72b4e1eccf21d91483ccd625eac833cf77ff9ab13628103d61b751fc64`

Tested product commit:

`49f424649836a39e10f9e835e71f32cf18674ea3`

Tested product blob:

`4e127584f680cde2af56f8d7f1c531368c1c2f4b`

Results:

```text
in-flight strong-lifetime discriminator  PASS
complete vm-device suite                 PASS
stable Clippy -D warnings                PASS
nightly rustfmt                          PASS
product diff identity before/after hook  PASS
git diff --check                         PASS
```

The workflow restored the exact product file after the test-only instrumentation and verified byte/diff identity before committing it.

## Corrected clean carrier

The tested product blob was minted directly on exact upstream without research workflow history:

Branch:

`teamleaderleo/cloud-hypervisor:review/ch-bus-r677-r678-r679-clean-v2`

Commit:

`d0ed124cc80e9d22c60cdc19adb3f935517fb9e3`

Parent:

`69d4c0a82ef15b2660906013bd87ae32668e7998`

The earlier clean commit `2edcf22f0bd35beff06ab2b4e132cf240e54d2f9` is superseded as a review carrier. Its original executed evidence remains useful for #677/#678/#679, but new compositions should use `d0ed124...`.

## Impact on #599

The previous clean #599 review stack used the superseded Bus commit as its first parent. The VMM BAR-reuse blob is independently tested and unchanged, but the combined source tree must be rerun on `d0ed124...` before the #599 clean carrier is considered current.

That recomposition is tracked separately; do not treat old internal review PR #60 as the canonical review surface after v2 stabilizes.

## Lesson

One-lock simplification was still the right repair boundary, but changing how the device reference was carried through that lock subtly weakened an existing lifetime property.

When replacing a caller/callee sequence with direct map manipulation, compare not only final state and errors but also **temporary ownership held during the operation**.
