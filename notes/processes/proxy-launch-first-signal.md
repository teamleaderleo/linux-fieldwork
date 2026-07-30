# Proxy launch must retain the first signal

A background child can exist before the shell stores `$!`. Temporary launch traps should retain the first cancellation signal until the child PID is owned. After registration, cleanup must use that retained status before ordinary terminating traps are restored.

A later signal must not overtake the first one between PID assignment and pending-signal dispatch. Test this boundary with two different signals and require the first status, one cleanup, no later work, and no surviving child.
