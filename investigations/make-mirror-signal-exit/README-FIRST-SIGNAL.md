# Proxy launch first-signal addendum

## TL;DR

The launch-window repair must not only remember a signal before `$!` is stored; it must also prevent a later signal from replacing the first one after PID registration and before pending-signal dispatch.

## Explain like I'm five

The script hears “stop” and writes it down. Before it acts, someone says “stop another way.” The first request must remain the reason the script reports when it cleans up.

## Why care

Losing first-signal identity makes cancellation reporting depend on a tiny timing interval. Supervisors and logs can receive the wrong cancellation reason even though the child is cleaned correctly.

## Proof

`tests/test_make_mirror_signal_first_signal.py` reconstructs the reviewed predecessor, sends TERM before PID assignment, then sends INT after assignment. The predecessor returns 130; the retained repair returns 143, cleans once, leaves no later-work marker, and reaps the proxy.

No full mirror build or public upstream interaction is included.
