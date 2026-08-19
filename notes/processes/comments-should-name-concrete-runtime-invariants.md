# Comments should name concrete runtime invariants

## In simple words

A project or kernel term can be historically correct and still be a weak local explanation. At a safety boundary, a useful comment says what concrete objects exist, how they relate, and what the code requires from them.

A Cloud Hypervisor VFIO review exposed this clearly. The inherited phrase `sparse mmap` was plausible domain vocabulary, but it did not uniquely communicate the runtime layout under discussion. A reviewer could reasonably read “sparse mmap” as sparse backing with a still-contiguous mapped range. The final comment became clearer when it named the separately mmap'd areas directly and then stated the range invariant.

## What I learned

The strongest version separated three jobs that had been compressed into one overloaded word:

```text
VFIO sparse-mmap
    domain / ABI provenance

separately mmap'd areas, possibly non-contiguous
    concrete runtime representation and geometry

requested range must fit within one mapping
    local safety invariant
```

That separation is useful because each sentence answers a different question.

The domain term explains where the layout can come from. The runtime nouns tell the reader what `find_user_address()` is actually iterating over. The invariant tells the reader why the following bounds check exists.

This was clearer than saying only that a region was “sparse” because `sparse` is overloaded. Depending on context, a reader may think about sparse files, punched holes, zero-filled pages, partially populated storage, or a device API that advertises selected mappable subranges. Those are related ideas, but none by itself establishes that one returned host pointer can safely span multiple independently created mappings.

`non-contiguous` also does only part of the job. It describes the concrete failing layout well, but the safety rule is stronger: each mmap area is its own mapping, so a requested range must fit inside one mapping even if two guest-address areas happened to be adjacent.

The local comment therefore benefits from saying both things:

```rust
// A VFIO MMIO region may be backed by multiple separately mmap'd areas,
// which may be non-contiguous. The requested range must fit within one mapping.
```

Why this version is stronger:

- it names the object the code actually owns and iterates over: mappings;
- it describes the surprising layout that makes the bug understandable;
- it states the condition enforced by the next check;
- it does not require the reader to know one historical term before understanding the safety argument;
- it can remain locally accurate even if the upstream mechanism producing those areas changes.

The reusable review question is:

> Does this comment make the reader decode project history, or does it name the runtime fact and the invariant directly?

Keep canonical domain vocabulary where provenance is the point: capability parsing, API-facing types, protocol documentation, or a higher-level explanation of how the case arises. At the enforcement site, prefer the concrete runtime nouns and the rule the code must uphold.

## Example

A weaker comment can be accurate but leave the important reasoning implicit:

```rust
// Sparse mappings can have gaps.
```

A stronger comment carries the local proof obligation:

```rust
// This region may be backed by multiple separately mmap'd areas.
// The requested range must fit within one mapping.
```

The second version tells a future reader what must stay true if the surrounding implementation changes.

## Environment and assumptions

- Context: Rust VMM code using independently created host memory mappings.
- Review lesson: applies most strongly around unsafe code, pointer arithmetic, range validation, ownership boundaries, and other places where a local invariant is easy to miss.

## Limits

This is a review heuristic, not a rule to replace every domain term with generic wording. If a canonical term has one clear meaning for the intended readers and directly explains the check, use it. Avoid turning obvious code into a paragraph of commentary.

The goal is precise local explanation: preserve domain terminology where it adds information, and spell out the concrete runtime condition where ambiguity would force the reader to reconstruct the reasoning.

## Related work

- `SOURCE_BRANCH_HYGIENE.md` for publication and upstream-candidate workflow rules.
