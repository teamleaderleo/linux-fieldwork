# Tests and evidence

## Exact retained identities

- Imported baseline source: `upstream/mmdebstrap/tarfilter`
- Imported source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Imported package revision: `debian/1.5.7-3`
- Imported resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
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

## Patch review

Retained source diff:

```diff
-                items.append(tarfile.REGTYPE)
+                items.extend((tarfile.REGTYPE, tarfile.AREGTYPE))
```

Complete retained diff reviewed: yes, through PR #77 at `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`.

Active overlap searched: yes inside Linux Fieldwork. Adjacent owners are units 01, 15, and 16; final candidate heads remain pending.

## Work performed in this session

- Refreshed #397 and all linked unit-22 carriers.
- Verified no earlier unit-22 packet or branch existed.
- Re-read issue #76, its checkpoint, PR #77 metadata/review, all three changed carrier files, import metadata, and imported source.
- Confirmed Linux Fieldwork `main` base `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`.
- Attempted current upstream clone with:

```sh
git clone --quiet https://salsa.debian.org/debian/mmdebstrap.git /mnt/data/mmdebstrap-unit22
```

Result:

```text
fatal: unable to access 'https://salsa.debian.org/debian/mmdebstrap.git/': Could not resolve host: salsa.debian.org
```

The temporary target was removed before the attempt and contains no retained checkout.

## Cleanup and rerun

- The original focused test uses in-memory archives and `TemporaryDirectory`; its exact-head CI receipt reports success.
- This session created no mounts, sockets, containers, background processes, or package installations.
- `/mnt/data/mmdebstrap-unit22` contains no successful checkout.
- A current-upstream rerun was unavailable because the runtime could not resolve Salsa for Git transport.

## Tests pending

1. Fetch exact current Salsa `master` and record commit/blob identities.
2. Apply `patches/0001-tarfilter-treat-nul-as-regular.patch` with a clean-tree receipt.
3. Place the regression in mmdebstrap's current native test suite.
4. Run the focused native test on baseline and candidate.
5. Run the relevant tarfilter test group or project gate on the exact candidate.
6. Clean the checkout and rerun the focused candidate test.
7. Compare/apply after final tarfilter unit ordering is known.

No current-upstream, native-suite, package-build, autopkgtest, lintian, or Salsa CI result is claimed by this packet.
