# Unit 16 clean expanded CI receipts

Recorded: 2026-08-02  
External contact: unauthorized; none made

## Clean technical-head run

- workflow run: `30691015678`
- job: `91345628785` (`lab-tools`)
- candidate/test head under comparison: `7fe46662141fa39a3b18ae1baba29b2b39f6c330`
- pull-request merge checkout: `2ebc22e9699521b41e943c492c6bdde4185d4ebc`
- conclusion: success

Observed gates:

- 4 changed patch files and 11 hunks validated;
- Python compilation passed;
- discovery retained 449 of 472 tests and removed 23 exact inherited duplicates;
- all 449 tests passed in 166.207 seconds;
- all focused final-name, inherited prefix/duplicate/lifecycle, and transform-scope unit-16 controls passed;
- shell syntax and command-help gates passed.

This is the clean result after replacing the inherited module's focused `TestCase` alias with a module import.

## Current packet-head rerun

- workflow run: `30691660479`
- job: `91347358106` (`lab-tools`)
- pull-request head: `c0926e099b98252e3d8f0c8463d53e9709e2a470`
- pull-request merge checkout: `20acc0c079a34776df2e81a447833df6e8673cbe`
- conclusion: success

Observed gates:

- 4 changed patch files and 11 hunks validated;
- Python compilation passed;
- discovery retained 449 of 472 tests and removed 23 exact inherited duplicates;
- all 449 tests passed in 151.721 seconds;
- all focused final-name, inherited prefix/duplicate/lifecycle, and transform-scope unit-16 controls passed;
- shell syntax and command-help gates passed.

Commits between the clean technical head and this packet head change documentation only. Candidate patches and unit-16 test bytes are unchanged.

## Interpretation

The selected final-projected-identity policy has a clean expanded technical-head result and a successful rerun at the current internal PR head. The next incomplete technical step is no longer CI: it is fetching exact current mmdebstrap `master`, comparing its `tarfilter` with imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`, and rebasing patches 0000 through 0002 with zero fuzz.
