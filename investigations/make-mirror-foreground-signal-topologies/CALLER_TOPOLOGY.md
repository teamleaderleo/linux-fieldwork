# `make_mirror.sh` caller and process-group topology

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

Repository search found no `setsid make_mirror` wrapper. The internal Linux Fieldwork workflows run focused regressions; they do not establish the full script's production invocation/session topology.

## Interpretation

A foreground command in an interactive job-control shell may receive its own process group. A noninteractive shell, CI step, scheduler, wrapper, or caller may use a different grouping arrangement. The repository evidence does not make either topology authoritative.

Therefore whole-process-group TERM is retained as a valid executed mitigation when the caller already owns a safe isolated group. It cannot be selected as the canonical repository contract for these reasons:

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

A source-level implementation could create isolated groups for specific child pipelines. That is a different direction from relying on the caller. It requires:

- `setsid` or an equivalent supervisor;
- an explicit group-leader PID;
- group signal and wait semantics;
- dependency and portability review;
- first-signal retention;
- cleanup and rerun controls;
- proof that no unrelated process enters the group.

The local output-pipeline model shows that `setsid /bin/sh -c PIPELINE` plus external `/bin/kill` of the negative group ID can stop all held stages. The target `/bin/sh` builtin group-kill spelling was not accepted as sufficient in that model; relying on `/bin/kill` adds another exact dependency to verify.

### Explicit all-stage supervisor

A dedicated helper could spawn and track every pipeline stage without relying on shell job groups. That enlarges the implementation and introduces a helper-language/API boundary, but it can make ownership explicit and testable.

## Current conclusion

Caller-group delivery is not a non-delegable user choice because the repository evidence already makes it unsuitable as the sole canonical answer. Comparative work should continue between:

- bounded internal process-group ownership;
- a dedicated all-stage pipeline supervisor;
- deliberately accepting eventual status correctness when the implementation cost exceeds the bounded operational impact.

No external contact is authorized or performed.
