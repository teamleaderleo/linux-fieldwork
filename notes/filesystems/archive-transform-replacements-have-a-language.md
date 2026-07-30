# Archive transform replacements have a language

## In simple words

A pathname transform contains two small languages: a pattern language and a replacement language. Reusing a regular-expression library handles only part of the contract. Replacement count, whole-match markers, backreferences, escaped delimiters, and flags can still differ from the command being emulated.

## Stable lesson

Compatibility wrappers should preserve the complete observable transform contract they advertise.

For GNU tar and sed-style substitutions:

- substitution is first-match-only unless `g` is present;
- `i` changes pattern matching, while `g` changes replacement count;
- unescaped `&` in the replacement means the complete matched text;
- escaped `&`, backslash, and the chosen delimiter are literal;
- duplicate or unsupported flags should fail clearly;
- transformed names may be referenced by hard-link and PAX metadata, which must be updated separately.

Calling Python `regex.sub(replacement, text)` silently chooses global replacement and Python replacement-string rules. That choice can rename additional path components even when the compiled pattern itself looks correct.

## Practical review checklist

When reviewing an archive rename implementation:

1. compare first-only and global cases;
2. compare case-sensitive and case-insensitive cases;
3. test the whole-match replacement marker;
4. test escaped special characters and the delimiter;
5. test invalid and duplicate flags;
6. test names referenced by hard links or extended headers;
7. use the documented reference tool as a differential oracle;
8. retain an unmodified-source negative control.

## Version and scope limits

This lesson comes from GNU tar 1.35, Python 3.13 behavior, and the imported `mmdebstrap` tarfilter blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` examined on 2026-07-30.

GNU tar's full transform grammar includes more than substitution count and basic replacement escapes. Pattern dialect, scope flags, case-conversion escapes, and link/reference rewriting require their own explicit tests.

Related investigation: `investigations/tarfilter-transform-semantics/README.md`.
