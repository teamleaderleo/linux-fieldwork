# Upstream issue draft

## Title

tarfilter path matching aliases dotfiles with ordinary names

## Body

`tarfilter` currently builds the absolute-looking path used by `--path-exclude` and `--path-include` with:

```python
name = "/" + member.name.lstrip("./")
```

`str.lstrip()` treats its argument as a character set. It removes every leading dot and slash instead of one or more complete archive prefixes.

This causes distinct members to share a matching key:

```text
.config    -> /config
config     -> /config
..name     -> /name
../config  -> /config
```

A minimal consequence is:

- `--path-exclude=/.config` can retain `.config`;
- `--path-exclude=/config` can remove both `.config` and `config`.

A focused correction can parse complete leading `/` and `./` prefixes, preserve the first real pathname component, and keep archive-root spellings matched as `/`.

A regression should cover both exclusion directions, include-after-exclude ordering, multi-dot names, leading parent components, archive-root spellings, and retained file/link metadata.

## Publication state

Fallback issue draft only. A tested code patch and pull-request draft exist internally. External issue creation requires explicit authorization.
