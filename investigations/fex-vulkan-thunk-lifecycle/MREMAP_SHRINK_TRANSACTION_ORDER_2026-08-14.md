# FEX `mremap` shrink transaction ordering hazard — 2026-08-14

Internal follow-up discovered by reviewing the green generalized remap carrier `f19f8940d31f51dac5117c17ab753c004a2ee1fd` after run `31793308929`.

## The simple matrix is green, but one multi-claim case remains

The generalized repair correctly handles the tested cases:

```text
forced move, no registration  -> revoked H
forced move + new registration -> new H active
in-place grow                  -> old H preserved
in-place shrink                -> retained H preserved, tail H revoked
```

The shrink test used two separate synthetic host keys:

```text
H_keep -> retained prefix
H_tail -> truncated tail
```

That does not exercise one H with claims in **both** pieces.

## Ordering bug in the current diagnostic helper

For `new_size < old_size` with `MREMAP_MAYMOVE`, the helper currently prepares:

1. retained prefix retirement;
2. truncated tail retirement.

Suppose one synthetic H owns two claims:

```text
H -> prefix target A   (active)
H -> tail target B     (standby)
```

Preparation then evolves state as:

```text
original: A active, B standby
prepare prefix: A removed, B promoted active
prepare tail:   B removed, H revoked
```

If the kernel keeps the remap in place, the desired final state is:

```text
A active
B retired
```

The current success path rolls the retained-prefix snapshot back, then commits the tail token. Rolling the prefix snapshot back restores the **pre-prefix** state, which still contains B. `CommitGuestRangeRetirement(tail_token)` only discards the tail snapshot; it does not reapply tail retirement. The tail claim can therefore be resurrected.

## Correct transaction ordering

Prepare the destructive piece first:

1. truncated tail;
2. retained prefix, only when movement is possible.

For the same H:

```text
original: A active, B standby
prepare tail:   B removed, A remains active
prepare prefix: A removed, H revoked
```

Then:

### In-place success

```text
rollback prefix -> restores state after tail retirement: A active, B gone
commit tail     -> discards tail snapshot
```

Correct final state.

### Moved success

```text
commit prefix
commit tail
```

Both pieces remain retired.

### Syscall failure

Rollback in reverse preparation order:

```text
rollback prefix -> state after tail retirement
rollback tail   -> original A active, B standby
```

Correct original state.

The same ordering also handles a callback whose unpacker/target dependencies span both pieces: retiring the tail first removes the callback once; the prefix snapshot then cannot accidentally capture a pre-tail version that would resurrect it during an in-place rollback.

## Required adversarial fixture

Before considering generalized shrink retirement settled, add a `MREMAP_MAYMOVE` shrink fixture with one H carrying both claims:

```text
H -> A in retained page 0 (active, returns 111)
H -> B in truncated page 1 (standby, returns 222)
```

Arrange the shrink to stay in place. After success:

- H must still return 111;
- reusing the tail VA for unrelated 333 code must never make H reach 333;
- diagnostics must show B retired and A active after prefix rollback.

A second forced-move shrink control should commit both pieces and leave H revoked until a new explicit registration.

This is a transaction-composition issue, separate from the already-proven single-claim remap semantics.