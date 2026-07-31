# LF-02 maintainer-script argument evidence repair

State: `dedicated lifecycle accepted — current-main repository gate pending`

## TL;DR

Run 25 completed the package lifecycle but its summary rejected the maintainer-script log because raw `$*` arguments spilled into ambiguous whitespace tokens.

The retained producer writes the exact argument vector as NUL-delimited hexadecimal in one `args_hex=` token, using `-` for an empty vector. The production summarizer requires and validates that field, and every synthetic summary fixture carries explicit argument evidence.

Dedicated run 33 completed the full install, upgrade, deliberate configure failure, recovery, and purge lifecycle with a schema-valid summary. This current-main carrier preserves those six accepted files and reruns repository integration without old stacked ancestry.

## Explain like I am five

The old log wrote all script arguments as one sentence, so spaces made the list impossible to recover. The new log puts invisible separators between arguments and stores the bytes as hexadecimal. The checker refuses missing or broken lists.

## Why care

Evidence that loses argument boundaries cannot prove which package-script lifecycle actually ran. A unit-only decoder is also insufficient if the production summarizer can silently accept a missing or corrupt field.

## Run 25: original evidence failure

- PR #178 head: `a3f7b0d09ec03cad457f09c2c466c759fcf94f54`;
- dedicated workflow: `30588652679` / 25;
- lifecycle job: `91025835702`;
- retained artifact: `8778845717`;
- artifact digest: `sha256:a973001e9b3bd3ae93937f7385d7cbb9bb9c242b80acbb188ff640908353668a`;
- artifact files: 313.

Summary validation stopped with:

```text
evidence validation failed: script log token is not key=value: '2.0'
```

The generated scripts had written:

```text
phase=preinst script_version=2.0 args=upgrade 1.0 2.0 dpkg_root=... cwd=...
```

The bare tokens were ambiguous. Run 25 therefore published no valid lifecycle disposition.

## Encoding contract

Generated scripts use:

```sh
args_hex=-
if [ "$#" -gt 0 ]; then
    args_hex=$(printf '%s\000' "$@" | od -An -tx1 | tr -d ' \n')
fi
```

The format:

- uses `$@`, preserving the original vector rather than joining through `$*`;
- NUL-delimits nonempty vectors, preserving empty arguments and boundaries;
- hexadecimal-encodes every byte so whitespace and Unicode cannot become record delimiters;
- uses `-` only for an empty vector.

## Production schema contract

`args_hex` is a required script-log field.

The summarizer accepts only:

- `-`; or
- nonempty valid hexadecimal whose decoded byte sequence ends in NUL.

It rejects missing fields, malformed hexadecimal, decoded empty bytes, missing trailing NUL, raw legacy whitespace, duplicate keys, and incomplete tokens.

## Repair sequence

### Run 26

Head `912ca6bfaee301ba72ec98f0fbb652b41c093764` passed focused encoding controls. Dedicated run `30638297780` / 26 failed before package execution because the same carrier accidentally removed `exist_ok=True` from the shared fixture writer. The retained generation restores repeatable writes below one `DEBIAN` parent and tests that behavior.

### Run 31

Head `9590cfe3a46ebb4141e02c67b85d62cc81c79cfc` made `args_hex` mandatory. Dedicated run `30638938917` / 31 correctly rejected old synthetic summary fixtures that still omitted the field. The retained fixture corpus now uses explicit `args_hex=-` where no arguments are present.

### Run 33 — accepted lifecycle

PR #356 head `a379140f79eae83b69acfad1b34dc12291cb9752` passed dedicated workflow `30639156586` / 33, including the independent artifact-receipt job.

Observed result:

- every fixture package built;
- guarded install, upgrade, deliberate configure failure, recovery, and purge completed;
- `summary.json` passed the production schema;
- deliberate configure failure was nonzero and left the target `half-configured`;
- recovery left the target `installed` with payload `3.1`;
- the modified conffile survived recovery;
- purge removed the principal conffile;
- unexpected mutations: 0;
- service actions: 32, all mapped by the retained policy;
- unresolved events: 0;
- host fingerprint unchanged;
- final disposition: `retain-mapped-behavior`.

That exact run owns the package lifecycle result. Current-main CI does not replace it.

## Current-main carrier

- source carrier: PR #356 exact head `a379140f79eae83b69acfad1b34dc12291cb9752`;
- branch: `restack/lf02-script-log-args-current-main`;
- current parent: main `523d5648d31fe35abc051467d1597e73fc61c79d`;
- historical first atomic six-blob commit: `b86366d067cd65a616b0d1e96306bbcb43cce7c3`;
- changed surface: six files;
- product/imported source changes: none;
- external contact: unauthorized and none.

The five executable/test blobs are byte-identical to the accepted #356 head and keep their original executable modes. The branch was atomically restacked after PR #359 moved main; this receipt is the only current-main-specific blob.

## Focused controls

The current-main gate must execute controls for:

- ordinary multiple arguments;
- empty argument inside a nonempty vector;
- spaces, tabs, newlines, and Unicode bytes;
- empty vector sentinel;
- missing `args_hex`;
- malformed hexadecimal;
- decoded empty bytes;
- missing trailing NUL;
- legacy raw whitespace rejection;
- repeatable writes below one fixture parent;
- generated source using `$@` and NUL-delimited hexadecimal rather than raw `$*`;
- complete production-summary fixtures and repository discovery.

## Evidence boundary

This unit repairs and validates the LF-02 evidence producer/schema and retains one accepted lifecycle result. It does not modify a product package, publish a release, contact an upstream project, or make a broader Debian lifecycle claim.

## Disposition

`CURRENT-MAIN RESTACK — HOLD FOR EXACT-HEAD REPOSITORY CI, COMPLETE SIX-FILE REVIEW, AND ROUTING OF THE HISTORICAL STACK`.

Internal Linux Fieldwork work only. No external contact.
