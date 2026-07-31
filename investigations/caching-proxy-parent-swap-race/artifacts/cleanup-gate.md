# Parent-swap suite cleanup gate

## TL;DR

The predecessor baseline reproduced the pathname-replacement behavior, and Linux Fieldwork CI run `30587406344` executed that baseline successfully. A later exact-head review also reproduced a lifecycle defect in the evidence harness: the command could exit successfully while retaining `complete-*` directories, hidden cache temporaries, or Python bytecode when the checkout became the temporary root.

The current-main carrier adds `tests/test_caching_proxy_parent_swap_cleanup.py`. It runs the complete parent-swap suite under dedicated ordinary and optimized-Python temporary roots, disables bytecode writes, inventories each runtime root after exit, and verifies that checkout-generated state remains unchanged.

## Why care

A green behavioral matrix is weaker when the matrix leaves state behind. Residue can make an immediate rerun depend on the prior run, conceal cleanup defects, or dirty the exact source being reviewed.

## Exact boundary

The gate checks:

- ordinary execution of `tests/test_caching_proxy_parent_swap_race.py`;
- the ordinary suite's existing optimized-child execution;
- a separate direct optimized execution with recursion disabled;
- empty dedicated temporary-root inventories after each execution;
- no new top-level `complete-*` paths;
- no new `__pycache__` paths in the test and composed-investigation trees.

The gate does not prove crash cleanup, host-wide temporary-directory hygiene, or cleanup outside the named suite. It establishes clean normal completion and immediate rerun prerequisites for this evidence carrier.

## Current state

Exact repair commit: `1d0d25185b5d974c266140c9e1e1b74cf7ccf713` plus this record.

Disposition: `HOLD` until the new exact head passes Linux Fieldwork CI and receives a complete four-file review. The successful predecessor run remains authoritative for the reproduced pathname behavior; the new head must establish the cleanup condition.

External contact authorized: `false`.
