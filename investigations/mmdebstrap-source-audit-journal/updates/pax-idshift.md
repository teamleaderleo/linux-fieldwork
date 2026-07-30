# Update — PAX ownership id shifting

## Finding

Issue #37 correctly records that `tarfilter --idshift` changes `TarInfo.uid` and `gid` but leaves existing PAX `uid`/`gid` strings intact. Those strings override the shifted fields when the output archive is parsed, so large-ID members silently keep their original ownership.

## Records

- Canonical issue: #37
- Candidate: PR #78
- Final validated head: `8d6443626e4338b180ec0533969bfe4d32b20d52`
- Exact-head CI: run `30538012863`, success
- Investigation: `investigations/tarfilter-pax-idshift/README.md`
- Retained patch: `investigations/tarfilter-pax-idshift/tarfilter-pax-idshift.patch`
- Regression: `tests/test_tarfilter_pax_idshift.py`

## Negative control and candidate boundary

The fixture contains one large-ID member that requires PAX numeric fields and one ordinary header-sized control. The unmodified source shifts only the ordinary member while the stale PAX values keep the large member unchanged. The candidate removes `uid` and `gid` from `member.pax_headers` after shifting so Python regenerates consistent values. Payload equality and a `-7` round trip are required and pass.

## Carrier history

The first retained patch revision failed before product execution because its hunk context did not apply. A reduced-context revision then applied at an unsafe line position and produced an `IndentationError`. Neither failure was treated as product evidence. The final revision replaces the complete nine-line `idshift` block, applies cleanly to the exact imported source, and executes the semantic assertions successfully.

## Impact

Ownership remapping can silently fail for accepted PAX archives, producing incorrect file ownership in downstream root filesystems and images.

## Authority

Internal Linux Fieldwork record only. No upstream contact.