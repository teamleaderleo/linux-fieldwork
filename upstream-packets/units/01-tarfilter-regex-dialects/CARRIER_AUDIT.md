# Carrier audit

Audit date: 2026-08-01  
Unit: issue #397, unit 01  
External contact: none; authorization remains false

## Audit rule

The audit followed the canonical unit record, source-bearing prerequisites, review-discovered proof carriers, and directly linked boundary records. It stopped where issue #397 assigns the behavior to another contribution unit or where the linked record explicitly characterizes a later grammar layer without changing unit 01 source.

## Canonical unit carriers

| Carrier | Exact identity | Role | Result |
| --- | --- | --- | --- |
| issue #397 unit 01 | unit 01 | priority, ready gate, authority | unit remains `ACTIVE` |
| issue #212 | release-candidate record | defect, evidence, draft, remaining gates | canonical unit record |
| issue #108 | dialect defect | default BRE versus `x` ERE boundary | owning defect record |
| PR #113 | head `54d5f67d84f1dfb10d1e2c9079026aea5e1f41dd`; merge `9a058c2f6df430fa788c958f61f3a3e6c995e713` | GNU tar 1.35 characterization | canonical negative control |
| PR #151 | head `4555c5c250c1afedb3947fd1a7b5a0323bd9d262`; merge `1a1952a78f79b2473f1f9513c1d5820f58987594` | core translator and repaired edge state | canonical product carrier |
| PR #202 | head `383e60c9e2a5666ec1c9e5815edf6126f5a6379f`; unmerged | parallel active-`(?` repair | duplicate/superseded |
| PR #216 | head `55d20a4cc08c93b34961c679bdb73458fea4c408`; merge `919ea3ed03e045f9a35b087549d76f4c0c5a9a0f` | malformed interval and unmatched-close repairs | canonical grammar repair |
| PR #203 | head `ee8b25d3f878a28db2e75076bb499bcc1c884101`; unmerged | initial positive guard controls | superseded proof carrier |
| PR #220 | head `bb0a79dec47958c6b865d4b382a44baff17ab736`; merge `ed49c01a85e9d363626db5d2973a33b67209e13b` | accepted neighbors of active-`(?` guard | canonical proof carrier |
| PR #211 | head `c76e01b3f2cc180a8d5dda2b94047361a39a372e`; merge `67cea0c3882250664fdf8d362c7c9d40ce4d6611` | upstream issue/MR drafts and release desk | draft/evidence carrier |

## Prerequisite transform chain

### Root semantic record — issue #36

Issue #36 records the broader mismatch between GNU tar/sed transform semantics and direct Python behavior. It names replacement count and `&` behavior as early defects and leaves the regex dialect slice to issue #108.

Its historical source statement names `josch/mmdebstrap` `main`, `tarfilter` commit `87b9b385b3` from 2024-09-13, and Debian snapshot `1.5.7-3`. The current unit packet uses the canonical Salsa project named by issue #212 and still requires a fresh exact `master` identity.

### Path/link/PAX precursor — issue #25 and PR #48

- issue #25 records unchanged hard-link targets and stale PAX `path`/`linkpath` after rewrites;
- imported source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
- PR #48 head `25f6bcda2a807a8901b3ff3e34f5581d6f057877`, merge `4d2550eb6a4e0765aed9f16897b4c4a9a39f119e`, retains the first path/link/PAX candidate;
- PR #48 encoded the wrong default symlink scope, leading to issue #63 and PR #68.

Classification: superseded precursor. PR #68 is the retained prerequisite carrier.

### Replacement semantics — issue #51 and PR #56

- issue #51 demonstrates Python global-by-default replacement versus GNU first-only behavior and rejection of `g` combinations;
- PR #56 head `640f414cb18cf47b3e803856392c720414bea333`, merge `ff3c9458cee438d16f8d99ca9e2e9b843d3766fe`, implements first/global selection, `i`/`g`, whole-match `&`, and escaped replacement handling;
- PR #56 explicitly retains Python pattern syntax as an evidence limit later addressed by unit 01.

Classification: historical component already composed into PR #68.

### Corrected target scopes — issue #63 and PR #68

- issue #63 records GNU tar's default `rsh` member, symlink-target, and hard-link-target scope and uppercase `S` opt-out;
- PR #68 head `1f8f16bf0841a720bdc1da727000c26a3ab13a09`, merge `e7388243f3436ceda16f9d5be70d5423cc379b9d`, corrects scope and composes PR #48/#56 behavior.

Classification: retained prerequisite source carrier, patch blob `1703984aa0c030e5131618a3541ee85bfd68ec65`.

### Numeric occurrence state — issue #98 and PR #102

- issue #98 defines numeric selectors, number-plus-global behavior, zero semantics, ordering, and last-number-run selection;
- PR #102 head `46f49d04639d6baf43243e5096175866c7e6a58e`, merge `78ba614fa7faf4f4cdff99bab832649c774fe1e7`, implements per-field selected-match state.

Classification: retained prerequisite source carrier, patch blob `81828a468854e7ec9ef4cda9626b9c57314afba3`.

## Review-discovered proof history

PR #151's review timeline established several repairs before promotion:

- branch-leading BRE `*`;
- literal `\0`;
- nested/repeated quantifier normalization;
- extended middle-position anchor behavior;
- consecutive basic interval rejection;
- active Python-only `(?...)` rejection.

PR #203 then identified the need for positive controls around the active-`(?` guard. PR #220 retained those controls on current main and recorded:

- hosted CI `30582215292` / 634 — success;
- direct inherited GNU differential suite — passed twice;
- current-main focused suite — 15/15;
- complete regex discovery — 38/38;
- zero product-source changes.

Classification: PR #220 is required proof evidence and should contribute regression cases to the final upstream patch.

## Explicitly separate linked records

### Issues #28/#29 and PR #33

- issue #28 aggregates dotfile identity and nested include-parent behavior;
- issue #29 owns byte-preserving no-option passthrough and GNU sparse preservation;
- PR #33 head `32a92eec0aed327dfad4e1ca0df51f6168b80a48` combines those findings with an LF-14 sparse stack and remained unmerged.

Issue #397 assigns these behaviors to later tarfilter units, including units 18, 20, and 21. They do not enter unit 01.

### Expression lists and persistent scope — issue #117 and PR #122

- issue #117 owns semicolon-separated substitution lists and persistent `flags=` target scopes;
- PR #122 head `430794881919aad8578c94fafac3b8a006cf335a`, merge `117ad6210a73cbb877981e6d6358d8f22a240c04`, is characterization only and leaves imported source unchanged.

Classification: later transform grammar layer, explicitly outside unit 01.

### Replacement case conversion — issue #125 and PR #135

- issue #125 owns GNU `\L`, `\U`, `\l`, `\u`, and `\E` replacement state;
- PR #135 head `ba80ca4a6640ff72076b7d24a150049b9352dfa4`, merge `34a78f8e1163dd1e9c8840aac88034589ef7610d`, is characterization only;
- GNU tar's empty-capture crash remains a separate safety boundary under issue #124.

Classification: later replacement-language layer, explicitly outside unit 01.

## Current package and overlap refresh

- Debian Sources lists `mmdebstrap 1.5.7-3` in sid/forky and a 11,453-byte `tarfilter`;
- Salsa tag `debian/1.5.7-3` is abbreviated `6fde9997`;
- a package-version mirror commit `574048f2a720057b75e56622003932f344dc700a` carries `tarfilter` blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`, equal to the Linux Fieldwork import;
- Debian BTS and web-indexed Salsa searches on 2026-08-01 exposed no equivalent tarfilter regex-dialect carrier;
- exact current Salsa `master`, raw canonical blob, and live complete issue/MR inventory remain unresolved.

## Audit conclusion

1. The canonical regex unit is issue #212, issue #108, PR #113, product PR #151, repair PR #216, and proof PR #220.
2. PR #202 and PR #203 are superseded internal carriers whose unique review evidence is retained.
3. PR #68 and PR #102 remain ordered prerequisites pending exact current-source inspection.
4. PR #48 and PR #56 are historical inputs already composed into PR #68.
5. Issues #28/#29 and PR #33 stay with later path/no-option units.
6. Issue #117/PR #122 and issue #125/PR #135 stay as later transform grammar layers.
7. Current Debian package evidence supports source-generation continuity but cannot replace exact Salsa `master` identity.
8. Current canonical retrieval, no-fuzz application/regeneration, current-source focused/native tests, exact live overlap search, and complete-diff review remain the first incomplete technical work.
