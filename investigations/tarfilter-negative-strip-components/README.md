# tarfilter negative strip-components validation

## Defect

`tarfilter` accepts negative `--strip-components` values because `argparse` converts them to integers and the rewrite loop later uses them as Python slice indices. A caller typo therefore rewrites paths from the end instead of failing.

For member `./a/b/file` the unmodified implementation produces:

```text
--strip-components=-1  -> file
--strip-components=-2  -> b/file
```

GNU tar rejects both values.

## Candidate

Reject a negative value immediately after argument parsing:

```python
if args.strip_components is not None and args.strip_components < 0:
    parser.error("--strip-components must be non-negative")
```

Zero and positive values remain valid.

## Regression contract

`tests/test_lf14_strip_components_validation.py`:

- requires the unmodified source to reproduce reverse-slice output for `-1` and `-2`;
- requires GNU tar to reject both values;
- applies only the bounded validation patch to an exact temporary source copy;
- requires candidate rejection, nonzero status, an empty output stream, and the diagnostic;
- requires `0` to retain the member path and payload;
- requires a positive control to keep normal stripping behavior.

The test intentionally does not apply unrelated sparse or transform patches. Parser validation is independent of those rewrite paths, and isolating the patch removes patch-order coupling.

## Source boundary

- imported implementation: `upstream/mmdebstrap/tarfilter`
- imported source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- defect: issue #58
- original stacked candidate: PR #59
- retained patch: `programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/scouts/LF-SCOUT-FS-01/artifacts/mmdebstrap-tarfilter-reject-negative-strip.patch`

The imported source remains unchanged. The regression patches only a temporary copy.

## Limits

This fix validates the sign of the integer. Extremely large positive values, non-integer syntax, repeated option precedence, and GNU tar diagnostic wording beyond rejection remain separate contracts.

## Authority

Internal Linux Fieldwork work only. No upstream contact is included or authorized.
