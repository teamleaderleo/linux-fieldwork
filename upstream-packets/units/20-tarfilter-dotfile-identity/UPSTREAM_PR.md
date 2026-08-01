# Upstream pull-request draft

## Title

tarfilter: preserve dotfile identity during path matching

## Body

Path-filter matching now removes only complete leading `/` and `./` archive syntax prefixes. Leading dots that belong to a filename or parent component remain part of the matching identity.

Previously, `member.name.lstrip("./")` treated its argument as a character set. That made `.config` alias `config` and could make `../config` match `/config`.

The new `tarfilter-path-dotfiles` test covers:

- excluding `.config` without excluding `config`;
- excluding `config` without excluding `.config`;
- preserving `..name`, `...name`, and `../config`;
- repeated and alternating archive prefix spellings;
- include-after-exclude restoration for `.config` and `..name`.

Focused validation:

```text
baseline test: exit 1
candidate test: exit 0
fresh patch application and rerun: exit 0
python3 -m py_compile: exit 0
```

The change is limited to `tarfilter`, one `coverage.txt` registration, and one focused test.

## Publication state

Internal draft. External contact and pull-request creation require explicit authorization.
