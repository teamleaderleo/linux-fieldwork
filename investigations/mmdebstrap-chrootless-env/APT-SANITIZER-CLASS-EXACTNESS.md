# Exact chrootless flag for the APT sanitizer receipt

## TL;DR

PR #368 retains the exact expected APT-managed outer-mutation argv:

```text
env -i PATH=... TMPDIR=... dpkg --force-not-root --force-script-chrootless --root=... --install ...
```

Its shared classifier, however, labeled any structurally selected `env -i ... dpkg` call as `sanitizer-dpkg`. That was broader than the written claim and broader than the direct-transaction receipt, which already requires exact `--force-script-chrootless` element membership.

This focused repair requires all three properties before assigning the sanitizer class:

1. `env` ignores the inherited environment;
2. the structurally selected command basename is `dpkg`;
3. the exact command argument `--force-script-chrootless` is present.

No product patch, transaction command, package fixture, workflow, or retained artifact is changed.

## Explain like I'm five

The receipt was labeling every clean-room delivery truck as *the package-script truck*. The real truck also carries a specific badge: `--force-script-chrootless`.

The repair checks the badge as its own argument. A sticker that merely contains the same words does not count.

## Why care

The APT transaction's raw evidence is strong, but automation should enforce the same boundary the report describes. Otherwise an unrelated `env -i dpkg --version` call could satisfy the class count while the governed chrootless package-script launch changed or disappeared.

Exact-element matching also prevents a look-alike argument such as:

```text
prefix--force-script-chrootless-suffix
```

from being promoted to authority evidence.

## Exact predecessor evidence

Canonical carrier at review start:

- PR #368;
- exact reviewed evidence head `67df2b723ef086989b24887302771069bcd14098`;
- current stacked base after runtime-guard additions `d776f908ac71b31f3c7c2ee068bc9e24bb816e17`;
- dedicated workflow `30644854355` / 110, success;
- artifact `8798986342`;
- ZIP SHA-256 `43cee5551d00fdc5da1bedf3fdce92250cac7366b22c32c54e294618f4718a69`.

The outer-mutation APT receipt contains exactly one `sanitizer-dpkg` record. Its argv includes exact elements for `-i`, canonical `PATH`, target `TMPDIR`, `dpkg`, `--force-not-root`, `--force-script-chrootless`, target `--root`, `--install`, and the local fixture package.

The candidate and inner mutation each retain host version/setup-hook calls but zero caller-path sanitizer records.

## Repair and controls

Changed files:

- `tools/classify_env_argv.py`;
- `tests/test_classify_env_argv.py`;
- this record.

Focused controls require:

- exact chrootless sanitizer → `sanitizer-dpkg`;
- dpkg without ignore-environment → not sanitizer;
- `env -i dpkg --version` → not sanitizer;
- substring look-alike flag → not sanitizer;
- shell text mentioning the flag → still host hook;
- `env -S` second parser → not guessed;
- directory summary still retains all four classes.

## Evidence boundary

The class remains intentionally structural rather than target-specific. It does not validate the exact root, TMPDIR, PATH, package path, or complete dpkg option order. Those values remain retained in the raw argv records and are cross-checked by transaction success, maintainer-script PATH observations, explicit configured/empty path controls, source mutation identity, and equal installed package sets.

A future claim that depends on one exact target or complete argv ordering should add a transaction-specific schema rather than silently overloading the shared class.

## Disposition

`EVIDENCE REPAIR` until exact-head repository CI and focused tests pass. Then compose into PR #368 or retain as a required follow-up before landing.

Internal Linux Fieldwork work only. No external contact is authorized or included.
