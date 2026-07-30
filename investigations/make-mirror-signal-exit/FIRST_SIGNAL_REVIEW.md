# First-signal review repair

The launch-window candidate records the first signal while the proxy PID is not yet owned. The repair keeps that temporary handler active through PID registration and dispatches the retained status before restoring ordinary terminating traps.

A focused competing-signal regression sends TERM before PID assignment and INT immediately after assignment. The earlier candidate reports INT status 130; the repaired candidate preserves the first TERM status 143, cleans once, leaves no later-work marker, and reaps the proxy.

This is internal evidence for issues #157 and #221. No external contact is authorized.
