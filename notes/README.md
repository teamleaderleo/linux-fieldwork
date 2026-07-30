# Linux Notes

This directory holds reusable Linux lessons that can be read independently of a full investigation.

## Use a note when

- the main result is an explanation, command, workflow, or source-reading lesson;
- a small demonstration is enough;
- the limits can be stated through distribution, version, shell, privilege, or environment assumptions;
- the work has no candidate patch or research claim requiring a full evidence record.

Start with [`../templates/note.md`](../templates/note.md).

## Categories

- [`shell/`](shell/) — shells, quoting, pipelines, scripts, and command behavior.
- [`filesystems/`](filesystems/) — paths, mounts, storage, filesystem semantics, and related tools.
- [`packaging/`](packaging/) — package formats, repositories, build systems, and package tooling.
- [`processes/`](processes/) — processes, signals, jobs, services, namespaces, and lifecycle behavior.
- [`permissions/`](permissions/) — users, groups, capabilities, privilege boundaries, and access control.
- [`debian/`](debian/) — Debian-specific policy, tooling, packaging, and project workflows.

Create another category when several notes share a clear topic that fits poorly in the existing set.

## Naming

Use short lowercase filenames with hyphens, such as:

- `shell/safe-positional-parameters.md`
- `filesystems/rename-across-mounts.md`
- `debian/source-vs-binary-packages.md`

## Promotion to an investigation

Open an investigation when a note produces a bounded uncertainty, suspected defect, candidate change, performance claim, security claim, or compatibility question. Keep the explanatory note and link the two records.
