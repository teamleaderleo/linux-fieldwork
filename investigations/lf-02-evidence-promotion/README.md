# LF-02 evidence and lifecycle promotion

## In simple words

Packet I reviewed the live LF-02 pull requests and separated durable evidence tooling from broad historical carriers. The first promotion slice carries portable provenance and a strict typed receipt onto current `main`. Product, lifecycle, D-Bus, target-comparison, and broad scout branches remain bounded by explicit repair or hold decisions.

Tracking: issue #194, Packet I.

## Worker and source boundary

- Worker: Helper I.
- Current-main base: `d344c942af4b55b5b0c71c8a66a8870fbf0db7bf`.
- Promoted evidence-contract content: `2459b2013d48560e446bb4c90b8658e93d559e10`.
- Schema repair source commit on the reviewed PR #129 stack: `3176d705504b0c3f68e8968eecc4b3157ac466c5`.
- Imported source trees are unchanged.
- Authority: internal Linux Fieldwork work only.

## Promoted slice

The current-main candidate transfers the unique evidence-quality work from PRs #115 and #129:

- versioned detached-head and GitHub Actions provenance;
- exact raw commands plus portable normalized command views;
- an exact six-phase execution inventory;
- an exact three-classification inventory;
- strict JSON integer and finite-number validation;
- monotonic phase durations with UTC wall-clock provenance;
- required regular-file artifacts and nonempty trace sets;
- explicit unresolved-evidence blocking;
- separate receipt status and research disposition;
- normal and optimized-Python regression coverage.

The generated summary is schema version 4. The retained hosted artifact on PR #129 remains schema version 3 evidence. A hosted schema-4 run is the remaining integration boundary; the internal contract and regression slice can merge independently.

## Exact validation

Executed from the current-main candidate:

```text
env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_lf02_summary_schema tests.test_lf02_evidence_provenance
...............
Ran 15 tests in 0.236s
OK

env PYTHONDONTWRITEBYTECODE=1 python3 -O -m unittest tests.test_lf02_summary_schema tests.test_lf02_evidence_provenance
...............
Ran 15 tests in 0.239s
OK

git diff --check main...2459b2013d48560e446bb4c90b8658e93d559e10
clean
```

The optimized run independently launches both normal and `python -O` subprocess validation for malformed typed input. Missing phase/classification inventories, missing artifacts, leftover phase-start records, boolean and string numerics, negative values, NaN, infinity, unresolved evidence, and comparison drift have focused controls.

## Complete-diff review

The complete `main...2459b2013d48560e446bb4c90b8658e93d559e10` diff contains six added files:

- two evidence tools;
- two durable contract records;
- two focused regression files.

No workflow, package fixture, imported source, hosted result, or external-contact carrier is included. This keeps the current-main unit independent from PR #21's broad scout runner and PR #129's old stacked base.

## Cleanup and rerun

Test-created Python cache directories were removed. Both focused suites were rerun from the extracted current-main candidate under normal and optimized Python with the same 15 passing tests.

## Composition and overlap

| Carrier | Reviewed exact head | Disposition | Boundary |
| --- | --- | --- | --- |
| PR #115 | `a1306af32b7357363ebdd09f44d3507c3e1c065a` | RETIRE after merge of this slice | Unique provenance and portable command-view work moved into the current-main candidate. |
| PR #129 | `183a925e0582bcb9c6fea64af271929cefc7bc1e` | RETIRE after merge of this slice | Unique typed-schema work moved and repaired at schema version 4; old hosted schema-3 receipt remains historical evidence. |
| PR #178 | `40c2b1ec89e4d8391bbcbe95a14f96a4a87760ca` | REPAIR | Guard recursive cleanup, implement terminating signal handling and child reaping, replace assertions, validate conffile siblings, and apply explicit decision precedence before hosted execution. |
| PR #109 | `f4c9fce1b0377f1fb61e3d13188c7294c3e1c692` | HOLD | The sanitizing `env` wrapper remains caller-PATH-resolved in both chrootless launch paths; exact-head product and parity gates are also pending. |
| PR #99 | `da604d9960b0517f0a79a23b0e54d59886a5e704` | REPAIR | Correlate D-Bus replies or rename the result as co-observation; add mixed-trace controls. |
| PR #104 | `b1c3c0227c3817d4e7bf1b50e5a3a4b00d36e958` | REPAIR | Fail on missing inputs and narrow the manifest claim or add content/metadata coverage; inherits PR #99's D-Bus boundary. |
| PR #21 | `f5c6b835bcc3283fc934718942c587593cb713af` | HOLD | Retain unique hosted host-service evidence while its destructive-path, parser, coverage, and rerun claims remain under review. |
| PR #22 | `ce2ccfa75efef0ffb4b678e97633179c38e14ada` | HOLD | Retain unique privileged integration evidence; executable gates and persistent-host cleanup limits remain incomplete. |

PR #115 and PR #129 become redundant carriers only after the current-main candidate lands. The remaining branches carry distinct product or hosted observations and stay open under their named boundaries.

## Disposition

`MERGE LOCALLY`

The evidence-contract slice is coherent on current `main`, has a complete reviewed diff, passes focused normal and optimized gates, and changes internal evidence tooling only.

## Remaining caveats

- Schema version 4 still needs a hosted full-matrix receipt before replacing the retained schema-3 artifact.
- This slice deliberately omits the historical runner and package fixture.
- The lifecycle, D-Bus, target-manifest, maintainer-script PATH, and broad scout carriers keep the dispositions above.

## External-contact state

No upstream issue, email, patch, merge request, comment, or review was sent or authorized.

## Next human decision

Merge the current-main evidence-contract slice locally, then retire PRs #115 and #129. Keep the other LF-02 carriers at their recorded repair or hold boundaries.
