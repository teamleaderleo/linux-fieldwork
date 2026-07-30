# Linux Research Programmes

This directory is the durable coordination surface for formal Linux and Debian research directions.

## Layout

```text
programmes/
├── registry.yml
├── <programme>/
│   ├── STATUS.md
│   └── lanes/
│       └── <lane-id>-<slug>/
│           ├── brief.md
│           └── artifacts/     # created when retained evidence exists
```

`registry.yml` keeps every plausible lane discoverable. A programme directory groups related questions and records current direction. A lane receives its own directory when its question, environment, first probe, promotion signal, and stop signal are clear enough for formal scouting.

A lane brief carries orientation, not a defect claim. Repeatable technical results belong in `investigations/`. General explanations belong in `notes/`.

## Lane lifecycle

- `inbox` — plausible question retained in the registry.
- `mapped` — a formal lane directory and bounded first probe exist.
- `active` — source reading or execution has begun under an owned investigation.
- `paused` — useful question waiting on environment, dependency, or capacity.
- `closed` — investigation or scouting produced a retained conclusion.
- `retired` — intentionally removed from consideration.

## Promotion rule

Promote a registry entry into a lane directory when:

1. the question is bounded;
2. likely source targets are named;
3. the required execution environment is understood;
4. a probe has distinguishing outcomes;
5. a meaningful consequence could justify continued work;
6. a clean stop condition exists.

Creating a programme or lane grants no authority to contact an upstream project.