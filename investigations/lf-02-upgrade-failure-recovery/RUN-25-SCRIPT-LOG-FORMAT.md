# LF-02 run 25 — maintainer-script arguments broke strict evidence parsing

State: `carrier-repair-created`

## Exact run

- PR #178 head: `a3f7b0d09ec03cad457f09c2c466c759fcf94f54`
- dedicated workflow: `30588652679` / 25
- lifecycle job: `91025835702`
- retained artifact: `8778845717`
- digest: `sha256:a973001e9b3bd3ae93937f7385d7cbb9bb9c242b80acbb188ff640908353668a`
- artifact files: 313

## What cleared

The workflow installed its trace dependency, compiled the LF-02 tools, passed shell syntax, and ran all 29 focused tests successfully.

The guarded lifecycle then executed and retained phase, snapshot, classifier, provenance, and host-fingerprint evidence.

## First failure

Summary validation stopped with:

```text
evidence validation failed: script log token is not key=value: '2.0'
```

The generated maintainer scripts wrote:

```sh
printf 'phase=%s script_version=%s args=%s dpkg_root=%s cwd=%s uid=%s gid=%s\n' \
    ... "$*" ...
```

A multi-argument invocation therefore produced records such as:

```text
phase=preinst script_version=2.0 args=upgrade 1.0 2.0 dpkg_root=... cwd=...
```

The summarizer deliberately splits the retained line on whitespace and rejects any token without `=`. The bare version tokens are ambiguous: they cannot be assigned back to exact argument boundaries from the log.

This is an evidence-producer failure, not lifecycle behavior. No disposition from run 25 is valid because `summary.json` was not published.

## Selected repair

Keep the existing strict `key=value` parser unchanged.

Encode the complete argument vector in one token:

```sh
args_hex=$(printf '%s\000' "$@" | od -An -tx1 | tr -d ' \n')
```

The encoding is:

- NUL-delimited, preserving argument boundaries;
- hexadecimal, so spaces, tabs, and newlines cannot become record delimiters;
- `-` for an empty argument vector, keeping the token nonempty under the parser contract.

The generated record uses `args_hex=...` instead of raw `args=...`.

## Executable regression

`tests/test_lf02_script_log_arguments.py`:

1. imports the actual fixture generator and summarizer;
2. executes a generated maintainer script in a disposable target;
3. supplies ordinary version arguments plus arguments containing spaces and a newline;
4. parses the retained record with the unchanged strict parser;
5. decodes the NUL-delimited hex and requires exact argument equality;
6. proves the explicit empty-vector sentinel;
7. retains the ambiguous run-25 shape as a rejecting control;
8. checks the generated source no longer records raw `$*` as a whitespace-delimited field.

## Other gate classification

Linux Fieldwork CI `30588652694` / 689 ran the same 29 LF-02 tests successfully. Its later generic shell/help step failed because this old stacked generation lacks repository paths now assumed by current main, including `scripts/capture-linux-context.sh`. That is a separate current-main promotion requirement, not a contradiction of this evidence-format repair.

## Next transition

Run repository CI and the dedicated LF-02 lifecycle on the exact repair head. A successful summary is required before interpreting package lifecycle, host effects, or disposition.

Internal Linux Fieldwork work only. No external contact.