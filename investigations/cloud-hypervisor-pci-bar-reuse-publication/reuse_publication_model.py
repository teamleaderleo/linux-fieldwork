#!/usr/bin/env python3
"""Deterministic oracle for PCI BAR old-address reuse publication.

This models only the cross-registry publication invariant. It is intentionally
independent of Cloud Hypervisor implementation details so current and proposed
release orderings can be compared without scheduler timing.
"""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class State:
    allocator_old: bool = True
    bus_old: bool = True
    ioevent_old: bool = False
    memslot_old: bool = False
    dma_old: bool = False

    def old_conflict_survives(self) -> bool:
        return self.bus_old or self.ioevent_old or self.memslot_old or self.dma_old


def hotplug_can_claim_old(state: State) -> bool:
    return not state.allocator_old


def early_publication_release(state: State, resources: tuple[str, ...], fail_at=None):
    """Model current/PoC ordering: allocator old is freed before teardown."""
    trace = [("start", state)]
    state = replace(state, allocator_old=False)
    trace.append(("allocator_free", state))

    if fail_at == "bus":
        return trace
    state = replace(state, bus_old=False)
    trace.append(("bus_remove", state))

    for resource in resources:
        # The reviewed VFIO PoC logs a P2P dma_unmap failure and continues.
        if resource == "dma" and fail_at == "dma":
            trace.append(("dma_remove_failed_continue", state))
            continue
        if fail_at == resource:
            return trace
        state = replace(state, **{f"{resource}_old": False})
        trace.append((f"{resource}_remove", state))

    return trace


def allocator_last_release(state: State, resources: tuple[str, ...], fail_at=None):
    """Candidate rule: allocator ownership is the last old-address lease."""
    trace = [("start", state)]

    for resource in resources:
        if fail_at == resource:
            return trace
        state = replace(state, **{f"{resource}_old": False})
        trace.append((f"{resource}_remove", state))

    if fail_at == "bus":
        return trace
    state = replace(state, bus_old=False)
    trace.append(("bus_remove", state))

    state = replace(state, allocator_old=False)
    trace.append(("allocator_free", state))
    return trace


def unsafe_publication_steps(trace):
    return [
        step
        for step, state in trace
        if hotplug_can_claim_old(state) and state.old_conflict_survives()
    ]


def run():
    cases = {
        "virtio_config": State(ioevent_old=True),
        "virtio_shm": State(memslot_old=True),
        "vfio_p2p": State(memslot_old=True, dma_old=True),
    }

    for name, state in cases.items():
        resources = tuple(
            resource
            for resource in ("ioevent", "memslot", "dma")
            if getattr(state, f"{resource}_old")
        )

        early = unsafe_publication_steps(early_publication_release(state, resources))
        late = unsafe_publication_steps(allocator_last_release(state, resources))
        print(f"{name}: early={early} allocator_last={late}")

        assert early, f"expected early-publication violation for {name}"
        assert not late, f"allocator-last exposed old address too early for {name}"

        for fail_at in ("bus",) + resources:
            trace = allocator_last_release(state, resources, fail_at=fail_at)
            assert not unsafe_publication_steps(trace), (name, fail_at, trace)

    print("allocator-last failure-injection invariant passed")


if __name__ == "__main__":
    run()
