# LF-03 — Rootless Ownership and Idmapped Mounts

## In simple words

User namespaces can make a root-owned target tree appear under shifted host IDs. This lane tests whether idmapped mounts provide a usable host view while preserving intended ownership on disk.

## Programme

[`Rootless execution, namespaces, and mounts`](../../STATUS.md)

## State

`mapped` — ready after a runner capability check.

## Question

Can idmapped mounts make rootless filesystem trees easier to inspect, edit, archive, and remove while preserving intended on-disk ownership?

## Why this could matter

Ownership translation affects cleanup, archive round-trips, package roots, container images, and administrator inspection. Inconsistent views can lose IDs or leave trees that ordinary workflows cannot manage.

## Likely targets

- Linux VFS idmapping;
- `util-linux` mount tools;
- `systemd-nsresourced`;
- `mmdebstrap` and container tooling.

## First probe

Create a small root-owned tree in a user namespace, expose it through an idmapped mount, and test stat, create, rename, archive, extract, and removal from both namespace views.

## Environment

Privileged CI or a VM with idmapped-mount support. Begin with a capability survey and kernel/filesystem compatibility check.

## Promotion signal

Promote when a tool reports inconsistent ownership, loses IDs during copy or archive, mishandles unmapped IDs, or leaves a tree that cannot be cleaned through the documented path.

## Stop signal

Close when ownership translation remains consistent and the selected tools preserve declared IDs.

## Expected outputs

- capability matrix;
- minimal ownership fixture;
- archive and cleanup observations;
- candidate investigation or retained environment limit.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.