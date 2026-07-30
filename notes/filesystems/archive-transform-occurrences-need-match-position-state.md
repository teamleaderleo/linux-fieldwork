# Archive transform occurrences need match-position state

## In simple words

A numbered sed-style substitution is a selection rule, not a replacement-count limit.

For `s/a/b/3`, the first two matches stay unchanged and only the third changes. Python's `re.sub(..., count=3)` changes the first three matches, so it cannot directly represent this contract.

## Reusable model

Represent substitution behavior with two independent values:

- **start match** — first match eligible for replacement;
- **continue after start** — whether later matches are also replaced.

This gives the core GNU/sed cases:

| Flags | Start match | Continue |
| --- | ---: | --- |
| none | 1 | no |
| `g` | 1 | yes |
| `N` | N | no |
| `Ng` or `gN` | N | yes |

A zero selector falls back to start match 1. For the GNU tar parser observed here, the last decimal run wins when several occur.

## Implementation lesson

Use a replacement callback with a per-string match counter:

1. return the original match before the selected position;
2. call the replacement-language function at the selected position;
3. call it for later matches only when global continuation is active;
4. otherwise return later matches unchanged.

Keep replacement expansion separate from match selection. Whole-match `&`, capture references, escaping, and future case-conversion syntax belong in the replacement function; occurrence selection decides only which matches receive that function.

## Archive-specific rule

Reset the counter for every path-bearing value. A member name, hard-link target, and symlink target each have their own first, second, and third matches. Sharing one counter across fields would make the result depend on member type and evaluation order.

After changing a member name or link target, clear stale PAX `path` or `linkpath` values so the archive writer regenerates metadata from the selected result.

## Validation pattern

A useful differential matrix includes:

- first-only and global controls;
- numeric-only and numeric-plus-global cases;
- number before and after letter flags;
- zero and a selector beyond the available matches;
- repeated decimal runs to expose parser precedence;
- case-insensitive composition;
- regular member, hard-link target, and symlink target fields;
- a predecessor-only negative control proving the new candidate is exercised.

Compare archive metadata directly with GNU tar. A successful process exit alone cannot detect a wrong transformed name.

## Provenance and limits

- Parent issue: #36.
- Numeric-selector issue: #98.
- Investigation: `investigations/tarfilter-transform-occurrence-selectors/`.
- Imported source: `upstream/mmdebstrap/tarfilter`, blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

This note covers occurrence selection. Regex dialect translation, multiple expressions, persistent `flags=` statements, and case-conversion replacement escapes need separate contracts.
