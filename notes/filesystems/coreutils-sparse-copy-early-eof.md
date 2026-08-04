# Coreutils `cp --sparse=always`: early EOF is a size transition

## In simple words

A sparse copy first creates a destination with the source's original size, then writes only the non-zero regions. If the source is shortened while the copy is running, a read can reach EOF before the original size.

Stopping the loop prevents the CPU spin, but that alone leaves the destination at the stale original size. The destination must also be shortened to the number of bytes actually consumed.

## Literal example

```text
metadata says source size = 2 GiB
copy reads 9 MiB
another process truncates source to 0
next read returns 0 (EOF)
```

Wrong responses:

- keep reading forever: CPU spin;
- break without truncating destination: 2 GiB destination with a stale trailing hole.

Expected response:

```text
truncate destination to 9 MiB
stop copying successfully
```

Black-box GNU `cp` 9.7 probes produced successful destinations sized to the amount read before the source truncation, not the original metadata size and not necessarily the source's eventual zero size.

## Implementation boundary

The Linux/Android sparse path currently:

1. opens source and destination;
2. records source metadata size;
3. pre-sizes destination to that value;
4. repeatedly reads a block and writes only blocks containing non-zero bytes;
5. advances by the read length.

A zero-length read before the recorded size is the missing transition. It means the recorded size is no longer reachable from this open source stream.

The narrow repair is:

- extract the read/write loop into a private helper over `Read` plus a real destination `File`;
- on `read == 0`, call `ftruncate(destination, current_offset)` and break;
- leave ordinary full-size sparse copying unchanged.

## Deterministic test design

Do not rely on a timed thread race in CI. Test the helper with:

- a reader containing a short byte sequence;
- a declared size larger than that sequence;
- a real temporary destination pre-sized to the declared size.

After the helper returns, assert:

- destination length equals the short sequence length;
- destination content equals the sequence;
- no trailing pre-sized region remains.

This directly tests the transition that caused the hang and avoids hiding scheduler flakiness behind a larger fixture.

## Scope boundary

This does not decide whether growing sources should be copied beyond their original metadata size, change sparse detection, modify reflink behavior, or alter stream handling. It addresses only EOF before the size snapshot.

## Authority

This note authorizes no upstream contact.