# uutils `stty size`: print-only queries must not write terminal state

## TL;DR

Current `stty size` reads and prints terminal dimensions, then unconditionally calls `tcsetattr()` with an unchanged `Termios` value. Job control treats that syscall as a terminal write. In a background process group, the kernel sends SIGTTOU and the process stops instead of exiting.

The controlled candidate skips the final `tcsetattr()` only when every parsed action is `ArgOptions::Print`. Mixed commands such as `stty -echo size` still apply terminal state.

## Explain like I'm five

`stty size` asks the terminal how big it is. After receiving the answer, it unnecessarily says, “set yourself to exactly how you already are.” A background job is not allowed to do that second operation, so the operating system freezes it.

The repair removes the unnecessary write while leaving real settings alone.

## Why care

The failure is a silent stopped process, not an ordinary command error. A parent waiting for the result can wait indefinitely. The reported case is an fzf preview process querying terminal height while fzf remains the foreground process group.

## Current state

- State: `EXECUTING`
- Canonical source base: `uutils/coreutils@21d4e9635b07a04f262cd8a5386f2987bca6cfef`
- Controlled branch: `teamleaderleo/coreutils:fieldwork/stty-size-read-only-13722`
- Current staged head: `d182649a1928e1501bf230d6ba14928352dcd1a0`
- Controlled draft PR: `teamleaderleo/coreutils#7`
- Matching canonical PR found: none at the recorded search boundary
- Source promotion: pending hosted verification
- External-contact state: no canonical-upstream contact authorized or made

## Baseline source path

`size` is parsed into `ArgOptions::Print(PrintSetting::Size)`. The settings branch then:

1. reads terminal state with `tcgetattr()`;
2. prints dimensions with `TIOCGWINSZ`;
3. calls `tcsetattr()` unconditionally.

The print action does not modify `Termios`, so step 3 is a no-op in state but not in kernel job-control semantics.

## Candidate

Add `requires_set_attr(args)`:

```text
true  when any parsed action is not Print
false when all parsed actions are Print
```

The action loop is unchanged. Only the final terminal-state write is guarded. This also correctly skips no-op writes for control-only operands such as `drain`; mixed print/mutation invocations still write.

## Verification design

### Unit boundary

- an empty parsed action set, as produced by control-only operands, does not require `tcsetattr`;
- `size` alone does not require `tcsetattr`;
- a real special setting does;
- `size` mixed with a real setting does.

### Job-control proof with negative control

The verifier creates a pseudo-terminal and a new session, keeps the session leader in the foreground process group, and launches each probe in a different background process group with SIGTTOU/SIGTTIN/SIGTSTP reset to their default dispositions.

It first runs a tiny Python negative control that performs a no-op `tcsetattr`. That process **must** stop with SIGTTOU. It then runs the candidate `stty size`, which **must** exit 0.

The same harness was exercised locally against the host kernel and GNU coreutils 9.7:

```text
negative control: stopped:22
GNU stty size:    exit:0
GNU stty drain:  exit:0
GNU size drain:  exit:0
GNU -echo size:  stopped:22
```

This proves that the test setup actually enforces job control and maps the print/control/mutation boundary.

### General regression checks

- complete `stty` integration module;
- rustfmt;
- focused clippy;
- source-only promotion fence.

## Evidence boundary

The controlled dynamic proof runs on Ubuntu 24.04. The issue report also covers macOS; broad fork CI must establish supported-platform compilation. A green Linux proof establishes the operation boundary but does not substitute for BSD/macOS runtime coverage.

## Next step

Inspect the hosted gate. If green, confirm the branch contains only `src/uu/stty/src/stty.rs`, review the final diff, and record exact commit/blob/job identities here.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other contact has been authorized or made.
