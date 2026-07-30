# Archive path normalization must not change filenames

## In simple words

Archive tools often accept member names with a structural `./` prefix while filtering rules use `/path` syntax. Converting between those forms must not strip dots that belong to the filename.

Using `name.lstrip("./")` is unsafe for matching because `lstrip()` removes any run of either character. It changes `.hidden`, `./.secret`, and `../path` rather than removing one defined prefix.

## What I learned

Define normalization as an explicit operation:

- remove repeated leading `./` archive prefixes when that is the chosen contract;
- remove leading `/` only to construct the filter's canonical absolute form;
- retain every other dot and component, including `.hidden` and `..`;
- never use a character-set stripping function when a prefix operation is intended.

When exclusion rules can be followed by descendant re-includes, preserve the original glob as well as its compiled matcher. A translated regular expression is an implementation detail and is not a reliable source for the user's literal prefix.

Parent retention asks whether the included literal prefix is equal to or below the parent:

```text
parent = /foo
included prefix = /foo/bar
```

The descendant prefix starts with `parent + "/"`; the inverse check is false.

## Source and provenance

- Project: imported `mmdebstrap`
- File: `upstream/mmdebstrap/tarfilter`
- Canonical issue: #28
- Investigation: `investigations/tarfilter-path-filter-matching/`

## Validation

The regression covers:

- top-level dotfiles with and without a structural `./` prefix;
- a `../`-prefixed member that must not become a different absolute path for matching;
- an excluded parent directory with an exactly re-included child;
- an excluded symlink parent with a re-included descendant.

The unmodified dotfile and parent-directory results are retained as negative controls.

## Limits

This lesson concerns filter-name identity. It does not declare a traversal archive safe to extract and does not resolve the security policy for following archive-created symlink parents. Wildcard-only include prefixes require separate policy because they provide no useful literal parent path.

## Related work

- Issue #28
- Issue #25 for hard-link and PAX path rewrites
- Issue #29 for no-option passthrough
