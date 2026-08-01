# Upstream issue draft

## Disposition

A standalone issue appears unnecessary because the patch and regression are small and self-contained. Use this draft only if the maintainer prefers issue-first discussion.

## Title

tarfilter path matching aliases dotfiles with ordinary names

## Body

`tarfilter` currently normalizes archive member names for path filtering with:

```python
name = "/" + member.name.lstrip("./")
```

`str.lstrip()` treats `"./"` as a set of characters. It removes filename dots as well as archive prefixes, so `.config` and `config` both match as `/config`. Parent-component spellings such as `../config` also collapse to `/config`.

A minimal archive containing `.config`, `config`, `..name`, `...name`, and their `./`-prefixed spellings shows both directions:

- `--path-exclude=/.config` fails to remove the dotfile;
- `--path-exclude=/config` removes the dotfile and `../config` along with the ordinary name.

The proposed correction consumes only complete leading `/` and `./` archive syntax prefixes. Dots belonging to the first pathname component remain part of the matching identity.

A focused test covers exclude and include behavior for `.config`, `..name`, `...name`, repeated and alternating archive prefixes, ordinary names, and `../config`.

No upstream contact has been made. This text remains an internal draft pending explicit authorization.
