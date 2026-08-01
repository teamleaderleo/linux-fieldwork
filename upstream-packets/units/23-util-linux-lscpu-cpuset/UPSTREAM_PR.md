# Withheld Debian packaging merge-request draft

Status: `DO NOT SEND — NEEDS FORK, candidate gates, source delta, and explicit authorization`

## Suggested title

`util-linux: clear failed cpuset output in trixie`

## Draft summary

This backports canonical util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` to the trixie package.

`ul_path_cpuparse()` freed a cpuset after malformed input while retaining its address in the caller's output slot. Later ordinary `lscpu` cleanup could free the stale address again. The patch clears the output immediately after the first free and preserves the existing error result and successful path.

## Demonstrated before submission

- Debian trixie `2.41-5` actual binary reproduces in text and JSON modes;
- exact Debian source retains the affected error path;
- canonical patch applies with `--fuzz=0`;
- patched binary package builds;
- upstream owns and has validated the correction.

## Required before submission

- candidate actual-binary matrix passes;
- valid output comparison passes;
- relevant native tests pass;
- package patch lives under Debian's selected upstream-stable path;
- `debian/patches/series` and changelog contain only the intended delta;
- source package and debdiff are retained;
- version and target suite follow release-team direction;
- external authorization is explicit.

## Proposed packaging delta

1. add the canonical patch with original authorship;
2. append one quilt-series entry;
3. add one stable-update changelog stanza;
4. retain source and binary test receipts.

No upstream util-linux change is proposed.
