# kmod depmod stream-error check ordering

## TL;DR

At `kmod-project/kmod` commit `65ac890492c96b88d10d8c92342a1b00ff603dba`, depmod's on-disk index path correctly refuses to publish a temporary file when the output callback, stream error indicator, or `fclose()` reports failure. That is a good publication boundary and is stronger than the libblkid cache path reviewed in another Fieldwork investigation.

One expression weakens the C portability of that check:

```c
ferr = ferror(fp) | fclose(fp);
```

The operands of ordinary binary operators do not impose left-to-right evaluation in C. If an implementation evaluates the right operand first, `fclose(fp)` ends the stream lifetime before `ferror(fp)` is evaluated. WG14 material explicitly describes ordinary operand evaluation order as unspecified and describes a `FILE` object's lifetime as ending when the associated file is closed.

On the local GCC 14.2 and Clang builds checked here, simple equivalent call-order probes evaluated the left call first at both `-O0` and `-O2`, so no current mainstream-compiler failure was reproduced. The defect class is therefore a latent portability / lifetime-ordering issue, not a demonstrated depmod data-loss bug on this environment.

The narrow repair is simply to sequence the operations:

```c
ferr = ferror(fp);
ferr |= fclose(fp);
```

That preserves both error sources while guaranteeing that the stream indicator is read before close invalidates the stream.

## Explain like I'm five

Depmod writes a new index file, checks whether writing went wrong, closes the file, and only then publishes it.

The intent is good. The source currently asks C to "check the error OR close the file" in one expression. C is allowed to choose which side happens first. If it chooses close first, the next check refers to a stream that has already ended.

Writing the two operations on separate statements removes the ambiguity.

## Why care

This code is the final gate before depmod publishes generated module index files. The current mainstream compilers checked here use the intended order, but the source contract should not depend on an operator evaluation choice when one operation invalidates the object used by the other.

The fix is tiny, changes no intended output, and makes the error/publication sequence explicit for future compilers and refactors.

## Source boundary

- Project: `kmod-project/kmod`
- Reviewed revision: `65ac890492c96b88d10d8c92342a1b00ff603dba`
- Relevant files:
  - `tools/depmod.c`
  - `shared/tmpfile.c`
- Origin commit for the expression:
  - `3f376cd87742246f00fe552596975a00ec5d60b1` — `depmod: use ferror and fclose to check for error` (2012-06-16)
- Current local compilers checked:
  - GCC 14.2.0
  - Clang available in the execution environment
- Relevant WG14 material:
  - https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1252.htm
  - https://www.open-std.org/jtc1/sc22/wg14/www/docs/n2668.pdf

## Bounded question

Does depmod guarantee that it reads a stream's error indicator before closing the stream whose state it is checking?

## Invariant

Every access to stream state must occur while that stream is alive. The final generated file should be published only after output generation, stream-state inspection, and close have completed in a defined lifecycle order.

## Source observations

### 1. The temporary-file publication boundary is otherwise careful

`shared/tmpfile.c` creates a temporary file in the target directory and publishes it with `renameat()` only when the caller requests publication.

The depmod output loop writes each generated index through that temporary file. After the callback returns, it checks callback status and stream/close status before `tmpfile_publish()`.

This means the high-level protocol already has the right phases:

```text
create temporary -> generate -> inspect/close -> publish
```

### 2. Stream inspection and close share one unordered expression

The current code computes:

```c
ferr = ferror(fp) | fclose(fp);
```

The intent is to retain either error condition while still executing `fclose()` even if `ferror()` is already nonzero. Bitwise `|` does provide that non-short-circuit property.

It does not, however, provide a left-to-right sequencing contract for the two operand evaluations.

### 3. The expression came from an error-handling improvement

Commit `3f376cd87742246f00fe552596975a00ec5d60b1` replaced an `ftell()`-based truncation check with the `ferror()` plus `fclose()` test. The commit message explicitly says the goal was to use both APIs to check for write errors.

So the intended semantics are clear: inspect stream error state and also capture final close/flush failure. The current single expression is an implementation detail, not an intentional close-before-inspect design.

## Standards pass

WG14 sequencing material states that, except for operators with explicit sequencing rules, operand evaluation order is unspecified. Bitwise `|` is not a left-to-right sequencing operator.

WG14 stream-lifetime material states that a `FILE` object's lifetime ends when the associated file is closed. Therefore the safe ordering is:

```text
ferror(live stream) -> fclose(stream)
```

The reverse ordering is outside the intended stream lifetime.

## Local compiler discriminator

A tiny call-order program used two side-effecting functions as operands of `|` and printed which function executed first.

Both GCC and Clang on this environment produced:

```text
ferror-side
fclose-side
```

at both `-O0` and `-O2`.

This is an important negative control: the investigation does not claim that current GCC/Clang depmod builds were observed calling `ferror()` after `fclose()`.

It establishes instead that the source relies on an ordering the language does not require.

## Cross-context pass

### Callback failure

Depmod separately retains the callback's negative return and releases the temporary file. This is independent of the ordering issue.

### Stream error before close

If `ferror()` executes first, the current expression detects the prior stream error and still executes `fclose()`. This is the intended behavior.

### Close/flush failure

The `fclose()` return is ORed into `ferr`, so a final flush/close failure blocks publication. This is also intended behavior.

### Right-operand-first evaluation

If `fclose()` executes first, the subsequent `ferror(fp)` no longer observes a live stream. The expression has no source-level sequencing rule preventing that ordering.

### Temporary-file publication

`tmpfile_publish()` occurs only after the `ferr` check. Once the two stream operations are explicitly sequenced, no separate publication redesign is needed for this finding.

## Candidate repair boundary

Keep the same variables and result contract; only make order explicit:

```c
ferr = ferror(fp);
ferr |= fclose(fp);
```

A logical `||` should not replace the bitwise operation because short-circuiting could skip `fclose()` after a pre-existing stream error. Two statements preserve unconditional close.

## Evidence boundary

Established:

- exact current depmod source still uses `ferror(fp) | fclose(fp)`;
- exact origin commit and intended dual-error-check purpose;
- current temporary-file publication waits for the combined error result;
- C/WG14 sequencing material does not give ordinary `|` operands a left-to-right order;
- WG14 stream-lifetime material ties `FILE` lifetime to the associated open file;
- local GCC and Clang probes currently evaluated the left operand first at `-O0` and `-O2`;
- no matching open or closed kmod issue was found with the searched `ferror fclose depmod` terms;
- no upstream contact occurred.

Not established:

- a real compiler/toolchain currently used by kmod that evaluates these two calls right-to-left in this function;
- a reproduced depmod crash, data loss, or bad published index from this expression;
- a full kmod build/test run with the two-statement candidate;
- exhaustive standards-lawyer review across every C language version kmod supports.

## Disposition

Retain as a small portability candidate. It is cheap to eliminate and sits in a high-consequence final-output gate, but it should not be presented as a reproduced runtime failure on current GCC/Clang evidence.

## External-contact state

No upstream greenlight was given. No upstream issue, pull request, comment, review, email, reaction, or other external contact was created.
