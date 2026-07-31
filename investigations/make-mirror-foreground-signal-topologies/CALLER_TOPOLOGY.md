# `make_mirror.sh` caller and process-group topology

## TL;DR

Whole-process-group cancellation is prompt in the model, but the repository does not document or enforce a safe isolated caller group for `make_mirror.sh`. Caller-group delivery therefore remains useful operational guidance for controlled wrappers, not the canonical source contract.

The main investigation stops without a broad internal supervision patch because the remaining latency has not been measured as harmful and the source-level alternative adds several ownership primitives and new utility dependencies.

## Explain like I'm five

Telling an entire room to stop works when the room contains only the program and its tools. The project does not promise that every caller gives the program a private room. Stopping the whole room could therefore stop unrelated work.

## Repository evidence

The retained upstream README documents direct invocation:

```text
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh
```

It does not require or demonstrate:

- `setsid`;
- a systemd scope or service;
- an explicit process-group wrapper;
- a supervisor that signals a negative process-group ID;
- a contract that every descendant belongs to one isolated group.

Repository search found no `setsid make_mirror` wrapper. The internal Linux Fieldwork workflows run focused regressions; they do not establish the full script's production invocation or session topology.

## Interpretation

A foreground command in an interactive job-control shell may receive its own process group. A noninteractive shell, CI step, scheduler, wrapper, or caller may use a different grouping arrangement. The repository evidence does not make either topology authoritative.

Therefore whole-process-group TERM is retained as a valid executed mitigation when the caller already owns a safe isolated group. It cannot be selected as the canonical repository contract because:

1. the documented command does not create or verify the group;
2. signaling a non-isolated group may affect unrelated caller processes;
3. owner-PID-only delivery remains a supported-looking but deferred path;
4. the script cannot tell whether its current group is safe to terminate wholesale;
5. full cancellation behavior would depend on undocumented caller policy.

## Consequence for alternatives

### Caller-owned process group

Disposition: **not selected as the repository answer**.

It remains useful operational guidance for controlled wrappers, but the current project cannot claim prompt cancellation from the documented invocation alone.

### Internal isolated groups

A source-level implementation could create isolated groups for specific child pipelines. Executed models show this is technically viable, including output capture and fallback chains. It requires:

- `setsid` or an equivalent supervisor;
- an explicit group-leader PID;
- group signal and wait semantics;
- dependency and portability review;
- first-signal retention;
- cleanup and rerun controls;
- proof that no unrelated process enters the group;
- separate parent-worker, simple-command, fallback, and output-capture ownership primitives.

The compatibility and implementation surface is disproportionate without evidence that the remaining cancellation delay is frequent or operationally harmful.

### Explicit all-stage supervisor

A dedicated helper could spawn and track every pipeline stage without relying on shell job groups. That introduces a helper-language and API boundary plus packaging and maintenance cost. No measured impact currently justifies it.

## Current conclusion

- Caller-group delivery: valid only under an explicitly isolated external wrapper.
- Internal process groups: technically viable, not retained.
- Dedicated supervisor: technically plausible, not justified.
- Canonical result: retain eventual correctness from PRs #224/#259 and hold broader source expansion.

Reopen only after measured harmful latency, a declared isolated-supervisor contract, explicit acceptance of group dependencies, or contradictory lifecycle evidence.

No external contact is authorized or performed.
