# Linux Fieldwork compendium

## In simple words

Linux Fieldwork already contains the evidence for a useful bug field guide: exact-source investigations, retained issues, reusable notes, failure matrices, review history, and practical bug lenses.

This directory extracts reusable structures from that evidence without moving or rewriting the original cases.

Working reader-facing title: **Fantastic Bugs and How to Find Them — Linux Fieldwork edition**.

```text
investigation / retained case
        ↓
Linux-derived reusable entry
        ↓
compare with sibling cases
        ↓
keep Linux-specific boundary
or graduate shared core into Fieldwork
```

The broader cross-domain design lives in `teamleaderleo/fieldwork#908`. Linux seed coordination lives in `teamleaderleo/linux-fieldwork#675`.

## Primary rule

**Case studies are evidence. Compendium entries are derived memory.**

An entry should say what generalizes, what remains local, and what would make the generalization false. Do not clean up the source history merely to make a pattern look elegant.

## What the seed is testing

The first tranche intentionally contains several kinds of objects:

- recurring bug species;
- invariants implied by cases;
- hunting techniques;
- repair patterns;
- regression patterns;
- candidate concepts and aliases;
- explicit examples of similar-looking bugs that should remain separate.

The physical directory is not the taxonomy. Metadata and relationships should eventually support cross-cutting search by lifecycle, persistence, publication, process ownership, authority, protocol, filesystem behavior, recovery, and testing technique.

## Evidence boundary

Entries may point to Linux Fieldwork issues, investigations, and reusable notes. Those sources own exact target revision, execution receipt, current status, environment, and external-contact state.

A compendium entry must not upgrade source-read evidence into executed evidence or turn a plausible consequence into a demonstrated one.

## Cross-domain graduation

A Linux pattern can graduate to the general Fieldwork compendium when comparison with a genuinely different domain preserves the same important structure.

```text
Linux case
+ unrelated-domain case
+ same invariant/owner relationship
+ meaningful limits
= stronger generic entry
```

Shared vocabulary alone is insufficient. `cleanup`, `ownership`, `ack`, and `terminal` are common words attached to many different state machines.

## Seed audit

See [`audits/2026-08-15-seed-corpus.md`](audits/2026-08-15-seed-corpus.md) for the first extraction matrix, separation decisions, and suggested next cases.
