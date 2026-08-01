# Source map

## Upstream source

| Item | Identity | Role |
| --- | --- | --- |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` | intended upstream destination |
| Intended branch | `main` | patch base |
| Current head observed | `77ec9be5417ee44c96343d2347145585da1b1f94` | current-upstream review base |
| Target file | `caching_proxy.py` | complete source change |
| Canonical file history shown upstream | last file change 2023-06-14, comment-only | indicates no visible source overlap after the imported baseline |
| Debian release cross-check | mmdebstrap 1.5.7, `caching_proxy.py` size 4,439 bytes | secondary source identity; raw-byte hash still pending |

## Linux Fieldwork source

| Path or carrier | Exact identity | Ownership |
| --- | --- | --- |
| `upstream/mmdebstrap/caching_proxy.py` | blob `e57a8516a0c76167894b05fc56be0e3165535488` | preserved imported baseline |
| `investigations/caching-proxy-complete-stack/compose.py` | merged PR #198 | routing entry point |
| `investigations/caching-proxy-complete-stack/compose_impl.py` | blob `00e28cc925ced0c01d9c8e300e7c94515367ca19` | complete semantic composer |
| `investigations/caching-proxy-complete-stack/inputs/` | merged PR #198 | focused snapshots absent from main when composed |
| `tests/test_caching_proxy_complete_stack.py` | PR #198 | seven-test complete matrix |
| `upstream-packets/units/02-caching-proxy-complete-repair/scripts/export_candidate.sh` | this branch | reproducible candidate and patch exporter |
| `patches/0001-caching-proxy-complete-repair.patch` | pending exporter run | proposed source patch |

## Linked carrier inventory

### Owning composition

- Issue #188 — complete request/cache/response integration boundary.
- PR #198 — merged nine-file composition; final head `5e69cd25e62d0e86364459d97c9df8568ff84187`; merge `8d9f7fa92f0cb2f553ca3578b78d7e04f4e4167f`; CI `30580697438` / 612.

### Focused request carriers

- PR #118 — authority validation, bodyless request framing, cache-key policy, descendant checks, and loopback bind. Closed after composition. Final displayed head `85e675ffb7618dabc26c8385b3f3fa74c8325b5a`; focused repaired evidence was retained in PR #198.
- Issue #127 / merged PR #139 — removes proxy credentials, standard hop-by-hop fields, and `Connection`-nominated fields while preserving repeated end-to-end fields. Merge commit `caf3262d2aa85057a2793bf758c7fc488bd0ccf2`.

### Focused response/cache carriers

- Issue #145 / PR #162 — canonical atomic-publication, downstream-framing, strict-length, transfer-coding core. Exact green head `055999d4c2d157abb9cb3d6dbf77a8cdacc91b1d`; CI `30578489609`.
- Issue #132 / PR #147 — pre-commit 502 versus post-commit log-and-close. Closed after composition; focused head displayed as `b0899c8417f23de54b5e5097dd7667539b37e949`.
- Issue #168 / PR #169 — explicit origin status validation surviving `python -O`. Exact green head `3ae3a6501653f273af25adae0279d072795e5a2f`; CI `30557655364`.

### Separate boundary

- Issue #227 — same-UID parent-component swap race. Exact imported composed source recorded there as `ed49c01a85e9d363626db5d2973a33b67209e13b`. This packet excludes the race and its fd-relative design question.

## Source ownership and review order

1. Request method/body framing and authority parsing.
2. Cache-key validation and pathname-level confinement.
3. Origin request-header sanitization.
4. Origin status, transfer-coding, and declared-length validation.
5. Downstream response-header normalization and commitment.
6. Exclusive temporary cache creation and atomic replacement.
7. Post-commit log-and-close behavior.
8. Loopback bind and lifecycle cleanup.

All eight mechanisms touch one handler lifecycle. Review the generated source as one candidate, then use focused carriers as mechanism records and negative controls.

## Destination map

- Proposed delivery: Forgejo fork and pull request.
- Controlled fork: `NEEDS FORK`.
- Candidate upstream branch: `NEEDS FORK`.
- External-contact authority: absent.
