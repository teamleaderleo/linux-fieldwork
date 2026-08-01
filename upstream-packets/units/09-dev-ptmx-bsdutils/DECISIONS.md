# Decisions

## 2026-08-01 — Keep unit 09 bounded to one test dependency

**Decision:** the owned correction is explicit selection of `bsdutils` in the generated root used by `tests/dev-ptmx`.

**Reason:** recovered Debian CI run `72574145` failed first and only on inner-root `script(1)`. `bsdutils` provides `/usr/bin/script`; runtime code and broader harness behavior are separate owners.

## 2026-08-01 — Retain the Linux Fieldwork candidate as evidence

**Decision:** preserve controlled-fork commit `43082a6bc959e2d7cefae48f52e045cc90869287`, the retained patch, exact-blob regression, and current-sid artifacts.

**Evidence:**

- baseline blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`;
- Linux Fieldwork candidate blob `fa93b4b845ff4927a72f258364bd920e8c7dc573`;
- one commit, one file, one insertion, one deletion;
- static run `30690010699` passed;
- current-sid runs `30690241513` and `30690452822` passed root and unshare variants and cleaned every generated root.

**Boundary:** the controlled repository follows the Deepin `1.5.7-3` import and is not canonical ancestry.

## 2026-08-01 — Use a networked internal runner for canonical read-only audit

**Decision:** clear the canonical-access hold through internal draft PR `#411` rather than treating local DNS failure as terminal.

**Audit identity:** run `30704384974`, job `91380861751`, artifact `8819850852`, digest `sha256:0504ab41ec727ffb87c5f803a6dc0611534ce0df0c0eadc2587a998808de9c2b`.

**Method:** mirror-clone canonical Forgejo and Debian Salsa repositories, inventory every ref, inspect complete `tests/dev-ptmx` history, and capture public issue, pull-request, BTS, and mailing-list search responses. All operations were read-only.

## 2026-08-01 — Correct the initial audit classifier

**Decision:** reject the initial summary field `corrected_include_history_present=false` as an ordering-sensitive false negative.

**Reason:** the first exact pickaxe searched Linux Fieldwork's ordering:

```text
bsdutils,gcc,libc6-dev,python3,passwd
```

Canonical history uses:

```text
gcc,libc6-dev,python3,passwd,bsdutils
```

Full path-history review found the exact canonical correction. Broad tracker and mailing-list regex hit counts also included unrelated substring matches and are secondary evidence.

## 2026-08-01 — Accept canonical successor ownership

**Decision:** canonical commit `c75b58e3c88b1f49626b9ee073e9e9688d38922c` owns the correction.

```text
author date: 2025-11-16T00:04:44+01:00
subject: make_mirror.sh,tests/dev-ptmx: explicitly install bsdutils for script utility
parent: 6de6403eca9d606a88ce8f6eb0bba097d9f7369e
resulting tests/dev-ptmx blob: 258a7f9579b2a2b91b6758952851296b44197ae0
```

The correction is present on canonical `develop` head `6e1e572bc49456daab7fd1274b1f3b8ec4a1c248` and tag `1.5.7+develop`. Canonical `main` head `77ec9be5417ee44c96343d2347145585da1b1f94` still has baseline blob `ca1cde...`.

## 2026-08-01 — Retire the external submission

**Decision:** move unit 09 from `HOLD` to `RETIRED`.

**Reason:** equivalent work already landed in canonical development history. Opening a competing issue or pull request would duplicate existing upstream ownership.

**Consequences:**

- no canonical fork branch or external pull request is needed;
- the Linux Fieldwork candidate remains historical confirmation only;
- close internal audit PR `#411` as completed evidence;
- close optional direct-run PR `#407` as unnecessary after preserving any result;
- normal observation of `develop` promotion requires no contact.

## 2026-08-01 — Preserve authorization boundary

**Decision:** no mmdebstrap or Debian upstream contact is created.

**Evidence:** no external issue, pull request, comment, review, email, or mailing-list message occurred during investigation, execution, or canonical audit.
