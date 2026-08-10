# Cloud Hypervisor — coredump temporary-pause restoration

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #587
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@915d359f97475b1a39d8561f8db514da9e692d19`
External-contact state: false; none occurred

## TL;DR

A coredump request against a Running VM temporarily pauses it and remembers that it should resume afterward. The implementation then performs multiple fallible setup/write steps. Resume is executed only at the successful tail.

Any post-pause error returns before the resume block, leaving the VM Paused even though it was Running when the request began.

The earliest low-cost discriminator is an output-path failure in `get_dump_state()`: file creation happens after pause, so an existing destination or uncreatable path should return a coredump error and leave the VM paused on current source.

## Explain like I'm five

Coredump says, “stop for a moment while I copy your state, then continue.”

If copying fails halfway through, the function currently leaves through an error exit before it reaches “continue.”

## Why care

Coredump is a debugging operation. Failure should report the dump failure while restoring a VM state that the coredump operation itself temporarily changed.

The code's `resume` boolean is direct intent evidence: it distinguishes a VM the coredump paused from one that was already paused.

## Current state

- State: `SCOPING`
- Exact working head: `915d359f97475b1a39d8561f8db514da9e692d19`
- Latest authoritative gate: current source review
- First incomplete step: run failure-state integration discriminator
- Cleanup state: no runtime resources created
- Next safe action: fail output creation against a Running VM and compare pre/post `vm.info`
- External-contact state: false; no upstream interaction authorized or made

## Question

Does every coredump exit restore a temporary pause owned by the coredump operation, and what is the smallest error-preserving cleanup pattern for failures after pause?

## Source

`GuestDebuggable for Vm::coredump()`:

```text
resume = false
Running -> pause(); resume = true
Paused  -> continue
other   -> reject

get_dump_state()?          # fallible
write_header()?            # fallible
write_note()?              # fallible
write_loads()?             # fallible
cpu_write_elf64_note()?    # fallible
cpu_write_vmm_note()?      # fallible
coredump memory?           # fallible

if resume {
    self.resume()?
}
```

No scope guard/finalizer exists between the owned pause and those early-return sites.

`Vmm::vm_coredump()` simply delegates to the VM and wraps errors; it does not inspect or restore VM state afterward.

## Earliest deterministic failure

`get_dump_state()` runs after pause and opens the destination with:

```text
OpenOptions::new()
    .read(true)
    .write(true)
    .create_new(true)
    .open(coredump_file_path)?
```

A path that already exists supplies a clean deterministic failure without exhausting storage or injecting a mid-write error.

Sequence:

```text
precreate destination file
VM state Running
request coredump to that file
coredump pauses VM
create_new fails with AlreadyExists
coredump returns Err
resume tail is skipped
```

## First probe

1. Start/boot a guest-debug-enabled x86_64 VM.
2. Pre-create the coredump destination path.
3. Read `vm.info`; require Running.
4. Call coredump to the existing path; require error.
5. Read `vm.info` again.

Expected current result:

```text
Running -> coredump error -> Paused
```

Control A: issue `vm.resume` manually and prove the guest returns to Running.

Control B: start with a Paused VM, trigger the same coredump failure, and prove it remains Paused. A candidate must not resume caller-owned paused state.

## Candidate boundary

The coredump operation owns only the pause it creates itself.

Required behavior:

```text
original Running:
    pause succeeds
    dump succeeds/fails
    resume is attempted on every post-pause exit

original Paused:
    no temporary resume obligation
```

A closure/scope-guard/finalizer can centralize this better than repeating resume beside every error.

## Error precedence

Candidate review should explicitly distinguish:

1. dump error + resume success -> return dump error;
2. dump success + resume error -> return resume error;
3. dump error + resume error -> preserve the dump failure as the primary operation failure while surfacing the failed state restoration through chain/log/combined context according to project conventions.

The third case matters because silently replacing the dump error with a resume error loses the original cause, while silently discarding the resume error hides the new VM-state problem.

## Adjacent contexts

### Pause failure

`resume` becomes true only after `pause()` succeeds, so a simple finalizer can avoid trying to undo a pause that never completed. Partial-failure semantics *inside* `Vm::pause()` are a separate owner.

### Partial dump file

A write failure after file creation can leave an incomplete output file. Decide deletion/retention separately; VM-state restoration is the first bounded defect.

### Paused input

Already-paused VM is the negative control and must remain paused regardless of dump result.

## Results

Established by source review:

- Running coredump pauses and records an obligation to resume;
- several fallible operations follow the pause;
- each can return directly through `?`;
- the only resume is at the success tail;
- the VMM/API caller supplies no outer recovery;
- an existing destination gives a deterministic post-pause failure.

Not yet executed:

- current binary state transition;
- candidate cleanup guard;
- guest-debug build/test gates.

## Evidence boundary

The state-transition consequence follows directly from current control flow. A runtime check is still required before promotion because guest-debug/coredump is feature-gated and the exact API test harness should capture the public state response.

## Stop condition

Close only if execution shows another owner restores the VM after the coredump function returns an error. Otherwise retain the temporary-state restoration boundary independent of partial-file cleanup.

## Next step

Run the existing-output-path failure and record the coredump error plus exact pre/post VM state.

## Authority

No upstream issue, pull request, comment, review, email, reaction, or other interaction is authorized or performed by this investigation.
