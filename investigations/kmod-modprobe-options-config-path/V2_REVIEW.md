# Exact-option transport v2 review

## State

- Review date: 2026-08-05
- Exact kmod base: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Baseline/native characterization: complete at `teamleaderleo/kmod#1@84ba8ae9db4f455965efa22afdd5cb177781106b`
- Candidate v1: compatibility-blocked at `teamleaderleo/kmod#2`
- Candidate v1 carrier repair head: `de1843a47153626c80e8687a5f7f9321d3beb026`
- Candidate v1 read-only validation: run `30928308898`, job `92056253742`, queued at the latest observation
- Separate v2 experiment: `teamleaderleo/kmod#3@a7309fba7c674107772d4921e8da98448845aac6`
- V2 snapshot run: `30929212556`, job `92059328241`, queued at the latest observation
- External contact: unauthorized; none made

## V1 carrier correction

Validation `30857305994` failed before source execution. The previous hunk repair omitted each hunk's final context line. The exact measured header corrections are:

```text
-42,5  +42,25  -> -42,6  +42,26
-47,5  +47,7   -> -47,6  +47,8
-70,8  +72,13  -> -70,9  +72,14
```

Only those counts changed. Candidate v1 logic remains held because it changes current raw-backslash parsing and does not establish bounded recursive transport.

## V2 model strengths

The executed Python model demonstrates that a versioned length-delimited record can:

- preserve arbitrary non-NUL argument bytes, including empty values, whitespace, quotes, and backslashes;
- reject malformed and non-canonical records;
- remain stable through repeated decode/rebuild cycles;
- leave the current legacy parser untouched when no exact record exists.

That is useful mechanism evidence, but it does not select a production policy.

## Policy and integration questions found in review

### 1. The record is caller-injectable

An environment variable described as internal is still supplied by the caller. A caller can set both the exact record and `MODPROBE_OPTIONS`, set an empty exact record to suppress legacy options, or provide a valid record with different policy.

A compiled experiment must define and test:

- exact-vs-legacy precedence;
- whether an empty exact record is authoritative;
- malformed exact input: hard failure versus legacy fallback;
- command-line options after exact ingress;
- behavior under privileged callers and sanitized environments.

No claim of authenticity should be made merely because the variable name is private.

### 2. Mixed-version recursion is not covered

A new parent may invoke an older `modprobe` through an install/remove command, or an older parent may invoke a new child. The exact record is invisible to old binaries, while a normalized legacy mirror may change raw-backslash, quote, empty-argument, or whitespace behavior.

The experiment must record, not assume, the compatibility boundary. At minimum test:

- new parent -> new child;
- new parent -> old/package child;
- old/package parent -> new child;
- whether the legacy mirror remains byte-compatible for inputs the old parser currently accepts.

### 3. `MODPROBE_OPTIONS` can contain more than `-C`, `-s`, `-q`, and `-v`

Current code prepends the complete private environment string, then selectively appends some parsed options back into the same variable. A replacement must decide whether the exact record carries:

- the complete parsed environment argv;
- only options kmod deliberately propagates;
- or a dedicated configuration-path list.

Each choice changes precedence and mixed-version behavior. The first compiled v2 should state the chosen subset explicitly.

### 4. Rebuilding requires provenance

To avoid recursive duplication while preserving additional command-line propagation, the implementation must distinguish inherited environment arguments from new command-line arguments. GNU `getopt_long()` may permute argv, so index-based provenance needs direct tests for:

- separate and attached option arguments;
- short and long forms;
- options appearing after a non-option;
- repeated `-C` values;
- clustered short options where applicable.

### 5. Stable exact state does not guarantee a stable process environment

If the legacy mirror continues to append recursively, total environment size can still grow even when the exact record is authoritative. If the mirror is rebuilt, old-child compatibility may change.

Measure both exact-record bytes and total relevant environment bytes through at least three real recursive install-command levels.

### 6. Shell and command topology matter

Install/remove commands execute through `system()`. Tests must cover quoting through the shell boundary, not only direct `execve()`-style argv reconstruction. Include:

- install and remove commands;
- nested commands that add another propagated option;
- success and child-failure status;
- no real kernel module insertion.

## Separate compiled experiment boundary

PR `teamleaderleo/kmod#3` starts from exact base and currently contains only a read-only source-snapshot workflow. It must not reuse or overwrite candidate-v1 patches.

The initial compiled v2 gate should require:

1. unchanged legacy parser source when no exact record exists;
2. exact-record malformed-input rejection;
3. explicit dual-variable precedence, including an empty exact record;
4. repeated and empty argument identity;
5. raw-backslash legacy controls with no exact record;
6. at least three recursive levels with stable exact and total environment sizes;
7. GCC and Clang sanitizer builds;
8. focused native tests plus standard final-head CI;
9. clean source state and retained patch/artifact hashes;
10. no public upstream contact.

## Current decision

Do not select candidate v1. Do not select the Python v2 model as a source design. Use PR #3 to compile one narrowly stated precedence policy, then compare its observed compatibility against current source and the package binary before deciding whether a second implementation strategy is required.
