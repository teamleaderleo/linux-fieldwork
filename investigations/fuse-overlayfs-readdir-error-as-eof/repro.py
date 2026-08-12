#!/usr/bin/env python3
"""Reduced state-machine discriminator for readdir error ownership."""

EIO = 5

# A directory that physically contains a, b, c. The backing iterator manages
# to return a, then hits an I/O error before b/c.
backing_events = [("entry", "a"), ("error", EIO), ("entry", "b"), ("entry", "c")]


def current_scan(events):
    """Current Option-only iterator: an error is indistinguishable from EOF."""
    cached = []
    for kind, value in events:
        if kind == "entry":
            cached.append(value)
            continue
        # DirStream returns None here. load_dir_impl exits the loop and then
        # marks the parent fully loaded.
        break
    return cached, True


def candidate_scan(events):
    """Result<Option<_>> iterator: error is retained and directory stays retryable."""
    cached = []
    for kind, value in events:
        if kind == "entry":
            cached.append(value)
            continue
        return cached, False, value
    return cached, True, 0


cached, loaded = current_scan(backing_events)
print("current cached:", cached)
print("current loaded:", loaded)
print("current lookup b:", "present" if "b" in cached else "ENOENT (cached false negative)")

cached, loaded, err = candidate_scan(backing_events)
print("candidate cached before error:", cached)
print("candidate loaded:", loaded)
print("candidate errno:", err)
print("candidate lookup b after retry:", "eligible for backing lookup" if not loaded else "blocked")
