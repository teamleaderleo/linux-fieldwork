# Upstream pull-request draft

## Title

tarfilter: preserve dotfile identity during path matching

## Body

Path-filter matching now removes complete leading archive prefixes instead of stripping every leading `.` and `/` character.

Previously, this conversion:

```python
name = "/" + member.name.lstrip("./")
```

made names such as `.config`, `..name`, and `../config` lose pathname data. As a result, a filter for `/config` could also match `.config`, while a filter for `/.config` could miss the requested member.

The new matching-key helper:

- removes complete leading `/` and `./` prefixes;
- preserves dots that belong to the first real component;
- preserves a leading `..` component;
- keeps archive-root spellings matched as `/`;
- leaves output member names and link targets unchanged.

The new `tarfilter-path-dotfiles` test covers:

- excluding `.config` without excluding `config`;
- excluding `config` without excluding `.config`;
- include-after-exclude and option-order behavior;
- `.config`, `..name`, `...name`, and leading parent components;
- repeated leading archive-prefix spellings;
- archive-root spellings;
- regular files, directories, symlinks, and hard links;
- retained payload bytes, modes, uid/gid, timestamps, PAX headers, and link targets.

Ordinary package members stored as `./path` retain dpkg-compatible filter identity. Additional repeated leading-prefix cases follow the pathname identity used by GNU tar during extraction.

The change is limited to `tarfilter`, one `coverage.txt` registration, and one focused test.

## Publication state

Internal draft. External contact and upstream pull-request creation require explicit authorization.
