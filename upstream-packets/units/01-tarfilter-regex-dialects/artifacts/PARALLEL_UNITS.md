# Parallel unit refresh — 2026-08-01

Every issue #397 unit branch from 01 through 23 exists.

Tarfilter-adjacent work reviewed:

| Unit | Branch | Current role relative to unit 01 |
| ---: | --- | --- |
| 15 | `upstream/unit-15-tarfilter-transform-metadata` | Direct prerequisite. Regenerated transform metadata/occurrence patch applies with zero fuzz and no offsets. Reused here verbatim. |
| 16 | `upstream/unit-16-tarfilter-type-hardlinks` | Explicitly vendors unit 15, then changes type-excluded hard-link identity. Later composition required; outside regex grammar. |
| 18 | `upstream/unit-18-tarfilter-no-option-passthrough` | Changes the no-option dispatch condition. Separate path from transform regex parsing. |
| 19 | `upstream/unit-19-tarfilter-pax-idshift` | Changes shifted PAX ownership metadata. Separate path from transform regex parsing. |
| 20 | `upstream/unit-20-tarfilter-dotfile-identity` | Changes path-filter normalization and adds an upstream-native test. Separate path from transform regex parsing. |
| 21 | `upstream/unit-21-tarfilter-parent-metadata` | Changes parent retention for include filters. Separate path from transform regex parsing. |
| 22 | `upstream/unit-22-tarfilter-regular-type-class` | Changes regular-file type classification. Separate path from transform regex parsing. |

Conclusion:

- unit 15 must precede unit 01 in the current retained composition;
- unit 16 already recognizes that same prerequisite;
- units 18–22 contain real updates but do not replace or supersede unit 01;
- final combined-upstream review must compose the selected independent units and resolve ordinary source-line overlap if several are submitted together.
