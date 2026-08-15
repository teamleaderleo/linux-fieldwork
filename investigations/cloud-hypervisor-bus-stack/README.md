# Cloud Hypervisor `vm-device::Bus` exact-current stack

## In simple words

Three independently proven bugs sit in the same small generic address-routing primitive on Cloud Hypervisor current `main`:

1. failed relocation can delete the old route (#677);
2. concurrent inserts can both admit overlapping routes (#678);
3. high-address overlap arithmetic panics in debug and wraps to a wrong answer in release (#679).

Each keeps its own discriminator and issue carrier. This record tracks their **composition**. The result is green: the three narrow repairs commute cleanly in one `vm-device/src/bus.rs` change on exact current source.

## Exact source and clean carrier

- canonical project: `cloud-hypervisor/cloud-hypervisor`
- exact upstream base rechecked at stack start: `69d4c0a82ef15b2660906013bd87ae32668e7998`
- tested research branch: `teamleaderleo/cloud-hypervisor:research/ch-bus-r677-r678-r679-stack`
- tested research commit: `eefcbbd5495996123c16ffa464bed83a27204ae4`
- clean review branch: `teamleaderleo/cloud-hypervisor:review/ch-bus-r677-r678-r679-clean`
- clean review commit: `2edcf22f0bd35beff06ab2b4e132cf240e54d2f9`
- tested/clean `vm-device/src/bus.rs` blob: `5ccf791aaec577a5af2f50bd398a1fbccc435342`

The clean review commit was minted directly on top of upstream `69d4c0...` using the exact tested source blob, so it carries no workflow/trigger history.

## Independent evidence entering the stack

### #677 — failed `update_range()` loses OLD

Authoritative individual run `31894236231`, artifact `9249356643`.

Repair invariant:

```text
validate NEW while OLD still exists
-> on conflict return with map unchanged
-> only then replace OLD with NEW
```

### #678 — concurrent `insert()` splits validation from commit

Authoritative individual run `31894509011`, artifact `9249424561`.

Repair invariant:

```text
one devices.write() guard
-> validate overlap
-> insert before releasing guard
```

The concurrency discriminator uses a test-only barrier so both threads cross the old validation point before either can commit. That proof remains workflow-only; the clean product source adds no test hook.

### #679 — overlap endpoint arithmetic overflows `u64`

Authoritative individual debug/release run `31894811738`, artifact `9249514376`.

Repair invariant:

```text
keep the existing half-open range relation
-> evaluate endpoint sums in u128
```

No new public range-rejection policy is introduced.

## Combined candidate

The stack intentionally preserves three separate claims:

```text
BusRange::overlaps(): representation-only endpoint widening
Bus::insert():        one-lock validation + commit
Bus::update_range():  one-lock preflight + OLD->NEW mutation
```

Permanent source regressions cover #677 and #679. #678 remains deterministically exercised by temporary barrier instrumentation around both baseline and combined candidate.

## Authoritative composition execution

- workflow run: `31896567927`
- job: `95040676799`
- artifact: `9249968763`
- artifact digest: `sha256:37560a56b4484a48ed5367cce65f17b352a0e2d94b5027864b498b4fbe0a982e`
- combined diff SHA-256: `5a1f3fc71dd74d38f88125beed668997f628fc09fe9d9dc1766f52b2ccedc5ff`

The run began by comparing `vm-device/src/bus.rs` byte-for-byte with upstream `69d4c0...` before injecting any test or candidate code.

### Losing baselines re-proved in the same run

```text
R677_BASELINE_RC=101
R678_BASELINE_RC=101
R679_DEBUG_BASELINE_RC=101
R679_RELEASE_BASELINE_RC=101
```

The baseline classifiers preserved the previously established failure identities:

- #677: conflict returns `Overlap`, then OLD reads as `MissingAddressRange`;
- #678: deterministic barrier lets both overlapping inserts succeed;
- #679 debug: endpoint addition panics with `attempt to add with overflow`;
- #679 release: wrapped arithmetic makes the real high-address overlap assertion fail.

### Combined candidate controls

The permanent #677 regression passed.

The #679 high-address regression passed in both debug and optimized release profiles.

Existing serial bus insert, read/write, and ordinary overlap controls passed.

The temporary #678 barrier was then re-injected **around the combined candidate**. With both threads released before the candidate write lock, exactly one insert succeeded and exactly one returned `Error::Overlap`.

### Full gates

```text
cargo test --locked -p vm-device                         7 passed, 0 failed
cargo clippy --locked -p vm-device --all-targets -- -D warnings  PASS
cargo +nightly fmt --all -- --check                       PASS
git diff --check                                          PASS
```

The tested source was DCO-signed on the research branch, then copied by exact blob identity into the clean review commit.

## Composition result

**PROVEN: #677, #678, and #679 compose cleanly on exact Cloud Hypervisor current main.**

The three repairs reinforce each other without merging their claims:

- range comparison becomes profile-independent;
- insertion validates and commits against one current map snapshot;
- relocation validates NEW before mutating OLD, under the same map lock.

This reduces the generic bus range lifecycle to a smaller set of observable states before returning to the wider PCI BAR publication problem.

## Scope boundary and next action

This record is limited to `vm-device::Bus` and its range map.

It does not absorb #599's wider PCI BAR allocator/ioeventfd/memslot publication transaction. That lifecycle has different owners.

With the generic map primitive now carrying a clean composed candidate, the next useful #599 experiment can reason about allocator lease release versus ioeventfd/memslot/device teardown without also carrying known `Bus` partial-state and overlap races in the local model.

External-contact state: false. Cloud Hypervisor upstream remained read-only throughout this work.
