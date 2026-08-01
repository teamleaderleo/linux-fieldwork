# Tests and evidence

## Exact retained identities

- Canonical upstream: `https://gitlab.mister-muffin.de/josch/mmdebstrap`
- Exact current upstream base: `main@77ec9be5417ee44c96343d2347145585da1b1f94`
- Current upstream `tarfilter`: still contains the defective `REGTYPE`/`0` mapping to `tarfile.REGTYPE` only
- Imported baseline source: `upstream/mmdebstrap/tarfilter`
- Imported source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Debian package revision: `debian/1.5.7-3`
- Debian package resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Retained candidate head: `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`
- Candidate merge commit: `4b9e24b0b20c1398dcae825310c6b7d0d5c273d0`
- Linux Fieldwork CI run: `30537313944`, success
- Focused test: `tests/test_tarfilter_legacy_regular_type.py` at the retained candidate head

## Retained command

```sh
python3 -m unittest tests.test_tarfilter_legacy_regular_type -v
```

The test applies the retained patch to an exact temporary copy of the imported source.

## Baseline/candidate matrix

| Case | Expected baseline | Retained exact-head result |
| --- | --- | --- |
| Fixture parses `REGTYPE`, `AREGTYPE`, `DIRTYPE` distinctly | yes | pass |
| Baseline `--type-exclude=REGTYPE` removes `zero-regular` | yes | pass |
| Baseline `--type-exclude=REGTYPE` leaks `nul-regular` | distinguishing negative control | pass |
| Baseline retains directory | yes | pass |
| Candidate `--type-exclude=REGTYPE` retains only directory | yes | pass |
| Candidate `--type-exclude=0` retains only directory | yes | pass |
| Candidate `--type-exclude=DIRTYPE` retains both regular encodings | yes | pass |
| Exact-head Linux Fieldwork CI | success | run `30537313944`, success |
| Exact-head review | accepted | PR #77 review `4818250508` |

## Current-upstream verification

Current upstream project inspection established:

- repository: `josch/mmdebstrap`;
- branch/head: `main@77ec9be5417ee44c96343d2347145585da1b1f94`;
- current `tarfilter` still uses:

```python
case "REGTYPE" | "0":
    items.append(tarfile.REGTYPE)
```

- upstream README documents the complete suite through `coverage.sh` and individual named tests through:

```sh
CMD=./mmdebstrap ./coverage.py --dist unstable <test-name>
```

Unit 15 independently records the current upstream `tarfilter` as matching imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

## Patch review

Retained source diff:

```diff
-                items.append(tarfile.REGTYPE)
+                items.extend((tarfile.REGTYPE, tarfile.AREGTYPE))
```

Complete retained diff reviewed: yes, through PR #77 at `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`.

Active overlap searched: yes. Unit 01 changes `TransformAction` regex grammar; unit 15 changes transform/link/PAX semantics; unit 16 changes hard-link dependency state. No direct source-owner overlap blocks unit 22. A later composed complete-gate run remains required.

## Work performed in this continuation

- Corrected unit state from `HOLD` to `ACTIVE`.
- Identified the canonical current upstream host, branch, and exact head.
- Confirmed the defect remains present on current upstream main.
- Identified the native individual-test runner and command form.
- Re-read units 01, 15, and 16 and removed the invented final-order dependency.
- Attempted exact source materialization from both upstream and Linux Fieldwork Git endpoints.

Git transport attempts failed in this runtime with DNS resolution errors:

```text
fatal: unable to access 'https://salsa.debian.org/debian/mmdebstrap.git/': Could not resolve host: salsa.debian.org
fatal: unable to access 'https://github.com/teamleaderleo/linux-fieldwork.git/': Could not resolve host: github.com
```

Current upstream identity and code were obtained through the official project web source; no local checkout or fresh execution is claimed.

## Cleanup and rerun

- The original focused test uses in-memory archives and `TemporaryDirectory`; its exact-head CI receipt reports success.
- This continuation created no mounts, sockets, containers, package installations, background processes, or credentials.
- Failed clone targets contain no successful checkout.
- Fresh exact-checkout execution remains pending because Git transport DNS failed in this runtime.

## Tests pending

1. Materialize `josch/mmdebstrap` exact commit `77ec9be5417ee44c96343d2347145585da1b1f94` in an environment with Git access.
2. Verify the checkout `tarfilter` blob and clean worktree.
3. Apply `patches/0001-tarfilter-treat-nul-as-regular.patch` with zero fuzz and zero offsets.
4. Add the archive regression to the current native test owner and name it in `coverage.py`.
5. Run the focused native test on baseline and candidate.
6. Run the relevant tarfilter/project gate on the exact candidate.
7. Clean the checkout and rerun the focused candidate test.
8. Compose with current adjacent tarfilter candidates for one complete-gate compatibility run.
9. Review the complete exact diff and active upstream overlap.

No current-checkout native-suite, package-build, complete `coverage.sh`, or upstream CI result is claimed by this packet.
