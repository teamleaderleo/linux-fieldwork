# Source map

## Exact source identities

| Item | Exact identity | Role |
| --- | --- | --- |
| User-controlled mmdebstrap source | `teamleaderleo/mmdebstrap` `master` at `574048f2a720057b75e56622003932f344dc700a` | Executed 1.5.7-3 source copy |
| Public upstream observed by unit 15 | `josch/mmdebstrap` `main` at `77ec9be5417ee44c96343d2347145585da1b1f94` | Current visible source reference |
| Base `tarfilter` | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` | Shared by the user fork, public-upstream relevant file, and Linux Fieldwork import |
| Clean prerequisite result | Git blob `adb330efcc941bf5e646f195c245a3184e42f8e2` | Unit-15 transform metadata/occurrence state |
| Final candidate result | Git blob `ca8e656c036172230c796a8a12cb17f262108c39` | Regenerated unit-01 regex state |
| Canonical contribution destination | `https://salsa.debian.org/debian/mmdebstrap` | External destination; exact head still unresolved |

## Current packet series

| Order | File | Exact identity | Result |
| ---: | --- | --- | --- |
| 1 | `patches/0001-transform-metadata-prerequisite.patch` | Git blob `38510533dc015182f3e87e9d2f3777eea5b8c93b`; SHA-256 `4d8cb2f180cb7798a15195c2dcfac164b409f68a18c69d507cfc624d4725703c` | base `ad776167...` → prerequisite `adb330ef...`; zero fuzz/offsets |
| 2 | `patches/0002-tarfilter-regex-dialects.patch` | Git blob `7e7d37a77b0215af033b0c97770c83cce130911a`; SHA-256 `2c3312f732b2fa0f1a04c92d7633c8a1e7bc9c2c7a6b52a6d150096d6a8f1746` | prerequisite `adb330ef...` → candidate `ca8e656c...`; zero fuzz/offsets |

The candidate file SHA-256 is `47e73119f2418fb1e7c47f3eb8f6e82e86a5903ff5c73c68fa5c5ac047ff6308`.

## Superseded application form

The historical core regex patch blob `2d7c457b83700d51b173efd0825128b6853a5f47` was tested after the clean prerequisite:

```text
hunk 1: offset +25
hunk 2: offset +19
hunk 3: failed
```

The historical edge blob `9994ac2272f23872b7f6e00a20f7282cb9b8cce3` therefore remains evidence only. `patches/0002-tarfilter-regex-dialects.patch` is the current carrier.

## Candidate code ownership

| Symbol or area | Change owner |
| --- | --- |
| delimiter parsing, replacement state, target scopes, PAX path/linkpath cleanup, numeric occurrence state | unit 15 prerequisite |
| `_active_branch_end()` | unit 01 contextual anchor translation |
| `_copy_bracket_expression()` | unit 01 bracket-state and unsupported POSIX boundary |
| `_quantifier_at()` / `_normalize_repeated_quantifiers()` | unit 01 repeated-quantifier and malformed-interval behavior |
| `_translate_pattern()` | unit 01 GNU basic/extended translation, Python-group guard, escapes, anchors, unmatched close |
| `x` transform flag and pre-compilation translation call | unit 01 parser integration |

## Tests and scripts

| File | Purpose |
| --- | --- |
| `scripts/materialize_and_run.sh` | Verifies the exact base blob, applies both patches with `--fuzz=0`, verifies intermediate/final blobs, compiles, runs the matrix, and cleans its temporary root. |
| `scripts/run_matrix.py` | Executes baseline/prerequisite controls and direct GNU tar 1.35 comparisons. |
| `artifacts/APPLICATION.txt` | Exact application and historical-carrier failure receipt. |
| `artifacts/FULL_MATRIX.txt` | Complete successful execution output. |
| `artifacts/HASHES.txt` | Blob and SHA-256 identities. |
| `artifacts/PARALLEL_UNITS.md` | Current neighboring issue #397 unit roles. |

## Carrier chain

| Carrier | Role |
| --- | --- |
| issue #212 | canonical release record |
| PR #113 | dialect characterization |
| PR #151 | original translator implementation |
| PR #216 | final malformed grammar repairs |
| PR #220 | accepted-neighbor proof |
| unit 15 branch | clean prerequisite patch and current visible upstream source identity |

## Parallel overlap

- Unit 15 is a required predecessor and is vendored exactly here.
- Unit 16 already vendors the same unit-15 prerequisite before its hard-link identity changes.
- Units 18–22 contain separate tarfilter corrections and remain later composition work.
- None supersedes the regex translator.

## Application command

```sh
sh upstream-packets/units/01-tarfilter-regex-dialects/scripts/materialize_and_run.sh
```

The wrapper fails closed on any unexpected base, prerequisite, or candidate blob.

## External branch state

- user-controlled source repository exists: `teamleaderleo/mmdebstrap`;
- candidate branch: `NEEDS BRANCH`;
- Salsa fork/MR: unauthorized and absent.
