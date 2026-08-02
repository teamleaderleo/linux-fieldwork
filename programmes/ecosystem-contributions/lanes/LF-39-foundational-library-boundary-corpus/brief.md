# LF-39 — Foundational-library boundary corpus

## TL;DR

Build a repeatable corpus of small, adversarial boundary cases for foundational Linux user-space libraries. Start with glibc `fnmatch(3)` extended matching because a synthetic rejecting input demonstrates rapid combinatorial growth without privileges, networking, hosted CI, or a full source build.

## Explain like I'm five

A wildcard matcher tries ways to split a word. If two choices can both consume the same letters, a failed match can make it retry almost every possible split. The first probe uses `*(a|aa)b` against many `a` characters followed by `c`: there is no match, so the matcher explores the ambiguous decompositions before giving up.

## Why care

Foundational libraries sit below many unrelated programs. A small pathological input can become a CPU-amplification boundary anywhere a caller enables the affected feature and lets an untrusted party influence the pattern or candidate string.

## Bounded question

Which compact inputs expose correctness, complexity, allocation, cleanup, locale, or representation boundaries in widely used foundational libraries, and which observations change a concrete upstream or downstream decision?

## Initial target classes

- glibc and other libc implementations;
- libarchive and compression libraries;
- URL, Unicode, configuration, terminal, and cryptographic support libraries;
- SQLite and other embedded persistence libraries;
- libraries with recursive parsers, backtracking matchers, stateful streaming APIs, or caller-owned cleanup contracts.

## First probe

Target: glibc `fnmatch(3)` with GNU `FNM_EXTMATCH`.

Discriminator:

- ambiguous rejecting input grows sharply with input length;
- matching input, unambiguous extended patterns, and the same syntax without `FNM_EXTMATCH` stay comparatively flat.

Initial pattern and candidate string:

```text
pattern: *(a|aa)b
string:  aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaac
```

## Environment

Current disposable Linux container, ordinary user, C compiler, installed system libraries, process-level timeouts, and temporary files only. Privileged or hosted execution is optional follow-up evidence, not a prerequisite for opening a bounded investigation.

## Adjacent contexts

Each investigation samples two to four decision-changing contexts:

- matching versus rejecting input;
- ambiguous versus prefix-disjoint alternatives;
- narrow API behavior versus a real downstream caller;
- installed distribution build versus exact upstream source;
- time growth versus allocation, stack, and cleanup behavior.

## Promotion signals

Promote a corpus entry into its own investigation when it has:

- an exact source or package identity;
- a minimal reproducer with a losing control;
- a measurable or semantic distinction;
- a named source owner;
- a bounded consequence and evidence limit;
- a concrete next decision such as regression test, algorithm review, consumer mitigation, or retained negative result.

## Stop signals

Stop or retain a negative result when:

- the apparent distinction disappears under repeated controlled execution;
- the source contract explicitly makes the observed cost unavoidable and callers already bound it;
- an equivalent active fix or authoritative report already owns the exact case;
- the next question requires a materially different platform, privilege boundary, or experiment.

## First investigation

[`glibc-fnmatch-extmatch-complexity`](../../../investigations/glibc-fnmatch-extmatch-complexity/README.md) — ambiguous `*()` and `+()` alternatives exhibit Fibonacci-like rejection-time growth on Debian glibc 2.41.

## Authority

This lane authorizes internal source reading, local synthetic execution, container work, tracked hypotheses, and candidate preparation. It does not authorize upstream issues, patches, mailing-list messages, comments, reviews, or other external contact.
