# Linux Fieldwork Targets

Targets are upstream projects or recurring Linux subsystems worth understanding across several lanes or investigations.

## Layout

```text
targets/
├── registry.yml
└── <target>/
    └── map.md
```

Keep low-cost possibilities in `registry.yml`. Create `targets/<slug>/map.md` when a target is imported, recurs across several lanes, carries policy or contribution complexity, or needs a durable source and test map.

A target entry grants no authority to open issues, send mail, submit patches, comment, review, or otherwise contact maintainers.

## Lifecycle

- `inbox` — plausible recurring target.
- `mapped` — a durable map exists.
- `active` — current investigations depend on the target.
- `watch` — useful target requiring reassessment before more work.
- `paused` — no current capacity or environment.
- `retired` — intentionally removed from the working set.