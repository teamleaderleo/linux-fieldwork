# Linux Research Landscape — 2026-07-30

## In simple words

This round identified 34 possible Linux and Debian lanes, grouped them into six durable programmes, and selected ten lanes for formal mapping. The canonical lane inventory now lives in [`../../../programmes/registry.yml`](../../../programmes/registry.yml).

## Outputs

- [`../../../programmes/`](../../../programmes/) — durable programmes, status files, and mapped lane directories.
- [`../../../programmes/registry.yml`](../../../programmes/registry.yml) — all 34 lane records and lifecycle states.
- [`selection.md`](selection.md) — why the ten mapped lanes were chosen first.
- [`sources.md`](sources.md) — primary and project-maintained source orientation.
- [`../../../targets/`](../../../targets/) — recurring upstream target registry and maps.

## Round method

The landscape used six filters:

1. consequential correctness, security, data integrity, cleanup, recovery, compatibility, or resource behavior;
2. a bounded first probe with distinguishing outcomes;
3. an exact source or package boundary;
4. known CI, privilege, VM, kernel, or hardware requirements;
5. repeatable evidence;
6. an explicit stop condition.

## Programme result

1. [`Rootless execution, namespaces, and mounts`](../../../programmes/rootless-execution/STATUS.md) — LF-01 through LF-06.
2. [`Debian packages, transactions, and builds`](../../../programmes/debian-packages/STATUS.md) — LF-07 through LF-13.
3. [`Filesystems, archives, and disk images`](../../../programmes/filesystems-images/STATUS.md) — LF-14 through LF-19.
4. [`Services, processes, and resources`](../../../programmes/services-resources/STATUS.md) — LF-20 through LF-24.
5. [`Security and networking boundaries`](../../../programmes/security-networking/STATUS.md) — LF-25 through LF-29.
6. [`Boot, devices, and deeper kernel work`](../../../programmes/boot-kernel/STATUS.md) — LF-30 through LF-34.

## Research boundary

This round maps questions and execution paths. It establishes no defect, affected version, production consequence, or upstream priority. Those claims belong in investigations tied to exact revisions and observed evidence.