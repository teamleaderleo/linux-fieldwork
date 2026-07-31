# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Upstream base | |
| Candidate head | |
| Linux Fieldwork head | |
| Platform/distribution | |
| Architecture | |
| Kernel | |
| Shell/runtime | |
| Privilege boundary | |
| Important tool versions | |

## Baseline reproducer

### Command

```text
...
```

### Expected distinguishing result

...

### Observed result

- status:
- stdout/stderr:
- changed state:
- surviving processes/files/resources:
- artifact or receipt:

## Candidate reproducer

### Command

```text
...
```

### Expected result

...

### Observed result

- status:
- stdout/stderr:
- changed state:
- surviving processes/files/resources:
- artifact or receipt:

## Matrix

| Case | Baseline | Candidate | Exact command or test | Result identity |
| --- | --- | --- | --- | --- |
| Primary negative control | | | | |
| Ordinary success control | | | | |
| Failure path | | | | |
| Cleanup | | | | |
| Immediate rerun | | | | |

Add format-, platform-, mode-, signal-, protocol-, and compatibility-specific rows required by the unit.

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Focused unit tests | | NOT RUN | |
| Relevant integration tests | | NOT RUN | |
| Formatting/lint | | NOT RUN | |
| Build/package test | | NOT RUN | |

## Linux Fieldwork retained gates

| Gate or fixture | Exact command/run | Result | Artifact/digest |
| --- | --- | --- | --- |
| | | | |

## Patch application and rebase

- base identity:
- patch application command:
- fuzz/offset result:
- conflict resolution:
- complete diff reviewed:
- active overlap searched:

## Cleanup and rerun

Record temporary paths, processes, sockets, mounts, locks, containers, images, cache entries, and source-tree state. State whether the same command passed immediately after cleanup.

## Tests not run

List every relevant unexecuted gate and why. Do not imply coverage from an adjacent or skipped job.

## Failure classification

For every red run, identify the first distinguishing owner: product, fixture, patch packaging, dependency, workflow, environment, capability, upstream change, or evidence parser.

## Final evidence statement

Summarize exactly what the executed matrix establishes and where the conclusion ends.
