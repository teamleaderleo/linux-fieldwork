# uutils `stty size`: print-only queries must not write terminal state

## TL;DR

Current `stty size` reads and prints terminal dimensions, then unconditionally calls `tcsetattr()` with an unchanged `Termios` value. POSIX job control treats that syscall as a terminal write. When `stty` runs in a background process group, the kernel sends SIGTTOU and the process stops instead of exiting.

The controlled candidate skips the final `tcsetattr()` only when every parsed action is `ArgOptions::Print`. Mixed commands such as `stty -echo size` still apply terminal state.

## Explain like I'm five

`stty size` asks the terminal how big it is. After getting the answer, it unnecessarily says, “set yourself to exactly how you already are.” A background job is not allowed to make that second request, so the operating system freezes it.

The repair removes the unnecessary second request while leaving real setting changes alone.

## Why care

The failure is a silent job-control stop, not an ordinary error. A parent waiting for the command can wait indefinitely. The reported real-world case is an fzf preview process that queries terminal height while fzf remains the foreground process group.

## Current state

- State: `EXECUTING`
- Canonical source base: `uutils/coreutils@21d4e9635b07a04f262cd8a5386f2987bca6cfef`
- Controlled source branch: `teamleaderleo/coreutils:fieldwork/stty-size-read-only-13722`
- Controlled staged head: `b4f17fbdc54a3cec77a75f8ae45392eef41497b4`
- Controlled draft PR: `teamleaderleo/coreutils#7`
- Matching canonical PR found: none at the recorded search boundary
- Source promotion: pending hosted verification
- External-contact state: no canonical-upstream contact authorized or made

## Baseline source path

`size` is parsed into `ArgOptions::Print(PrintSetting::Size)`. The settings branch then:

1. reads `Termios` with `tcgetattr()`;
2. prints the dimensions with `TIOCGWINSZ`;
3. calls `tcsetattr()` unconditionally.

The print action never modifies `Termios`, so step 3 is a no-op in state but not in kernel job-control semantics.

## Candidate

Add `requires_set_attr(args)`:

```text
true  when any parsed action is not Print
false when all parsed actions are Print
```

The existing action loop remains unchanged. Only the final call is guarded:

```text
if requires_set_attr(valid_args):
    tcsetattr(...)
```

This preserves argument ordering and mixed print/mutation behavior.

## Verification design

### Unit boundary

- `size` alone does not require `tcsetattr`;
- a real special setting does;
- `size` mixed with a real setting does.

### Job-control proof

The hosted verifier:

1. creates a pseudo-terminal;
2. creates a new session and makes the PTY its controlling terminal;
3. keeps the session leader's process group in the foreground;
4. launches `stty size` in a different, background process group;
5. waits with `WUNTRACED`;
6. requires normal exit 0 and rejects a SIGTTOU-stopped state.

This tests the actual kernel behavior without relying on the runner having an interactive terminal.

### General regression checks

- complete `stty` integration module;
- rustfmt;
- focused clippy;
- source-only promotion fence.

## Evidence boundary

The issue report contains macOS reproduction. The controlled dynamic proof initially runs on Ubuntu 24.04; broad fork CI must establish other supported-platform compilation. The candidate intentionally addresses print-only actions as a class rather than special-casing the string `size`.

## Next step

Inspect the first hosted gate. If green, confirm the controlled branch contains only `src/uu/stty/src/stty.rs`, review the final diff, and record exact commit/blob/job identities here.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other contact has been authorized or made.
