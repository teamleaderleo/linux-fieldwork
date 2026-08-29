#!/usr/bin/env python3
"""Reduced GL.iNet DPI/Netify boot-order model.

The live source identities and observed process state belong in README.md. This
model retains only the state transitions needed to distinguish three service
link arrangements without touching a router or starting a service.
"""

from __future__ import annotations

from itertools import product


CASES = tuple(product((0, 1), repeat=3))
VARIANTS = {
    "current": ("S99gl_dpi", "S99gl_dpi_flow_statistics", "S99netifyd"),
    "netify_start_98": ("S99gl_dpi", "S99gl_dpi_flow_statistics", "S98netifyd"),
    "netify_disabled": ("S99gl_dpi", "S99gl_dpi_flow_statistics"),
}


def simulate(entries: tuple[str, ...], flags: tuple[int, int, int]) -> bool:
    """Return whether the enabled Netify instance is running after boot."""
    netify_running = False
    for entry in sorted(entries):
        if entry.endswith("gl_dpi"):
            if not any(flags):
                netify_running = False
        elif entry.endswith("netifyd"):
            netify_running = True
        elif entry.endswith("gl_dpi_flow_statistics"):
            # Exact live sibling source neither starts nor stops Netify.
            pass
        else:  # Keep the model closed when a future service is introduced.
            raise AssertionError(f"unmodelled startup entry: {entry}")
    return netify_running


def verify() -> None:
    assert tuple(sorted(VARIANTS["current"])) == (
        "S99gl_dpi",
        "S99gl_dpi_flow_statistics",
        "S99netifyd",
    )
    assert tuple(sorted(VARIANTS["netify_start_98"])) == (
        "S98netifyd",
        "S99gl_dpi",
        "S99gl_dpi_flow_statistics",
    )

    results = {
        variant: {flags: simulate(entries, flags) for flags in CASES}
        for variant, entries in VARIANTS.items()
    }

    all_off = (0, 0, 0)
    single_consumers = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    any_consumers = tuple(flags for flags in CASES if any(flags))

    # Exact current ordering reproduces the observed unused resident process.
    assert results["current"][all_off] is True
    assert all(results["current"][flags] for flags in any_consumers)

    # Moving only Netify earlier corrects all-off without losing any one-consumer case.
    assert results["netify_start_98"][all_off] is False
    assert all(results["netify_start_98"][flags] for flags in any_consumers)

    # The live mitigation is correct only while every consumer remains off.
    assert results["netify_disabled"][all_off] is False
    assert not any(results["netify_disabled"][flags] for flags in any_consumers)

    print("variant qos flow content final_netify")
    for variant in VARIANTS:
        for flags in (all_off, *single_consumers):
            flag_text = " ".join(str(flag) for flag in flags)
            state = "running" if results[variant][flags] else "stopped"
            print(f"{variant} {flag_text} {state}")


if __name__ == "__main__":
    verify()
