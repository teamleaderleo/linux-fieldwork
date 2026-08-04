# uutils `pr`: numeric input bounds and page-geometry overflow

## TL;DR

`pr` parses several user-controlled geometry values as unrestricted `usize`. Huge values can panic under overflow checks, silently wrap in release builds, or reach impossible allocation sizes.

The related reports are not all the same defect:

- `-N` / first line number needs the GNU input-domain bound;
- `-l` / page length and column count need both input-domain bounds and checked derived geometry;
- a derived product can be invalid even when each operand is individually accepted.

This investigation remains in `SCOPING`. Saturating arithmetic is not an acceptable repair because it would turn invalid requests into misleading layout.

## Explain like I'm five

`pr` lets the user say how many lines and columns a page has. It currently accepts numbers as large as the computer can spell, then multiplies and allocates with them.

The right fix is not “when the multiplication breaks, pretend it is the biggest number.” The right fix is to reject numbers outside the command's documented numeric domain and reject page shapes that cannot be represented safely.

## Why care

Depending on build settings, the same input can:

- abort with an arithmetic-overflow panic;
- abort with a vector capacity overflow;
- wrap silently and produce inconsistent pagination;
- attempt impractically large allocations.

The behavior is controlled entirely by command-line input.

## Current state

- State: `SCOPING`
- Canonical source reviewed: `uutils/coreutils@21d4e9635b07a04f262cd8a5386f2987bca6cfef`
- Issues: `#13734`, related `#12996`
- Matching canonical PR found: none at the recorded search boundary
- Controlled source candidate: none
- External-contact state: no canonical-upstream contact authorized or made

## Current source boundary

`parse_usize()` parses option values directly into `usize` and emits a generic option error only when parsing itself fails.

Relevant consumers include:

- `FIRST_LINE_NUMBER` (`-N`), later incremented with `line_num += 1`;
- `PAGE_LENGTH` (`-l`), used to derive content lines per page;
- `COLUMN` and legacy `-COLUMN` operands;
- products such as `content_lines_per_page * columns`, used both as layout gates and allocation dimensions.

On a 64-bit build, values far beyond the GNU command's domain can parse successfully and reach those operations.

## GNU 9.7 black-box receipt

### Individual input domain

For all three numeric surfaces below, GNU accepts `2147483647` (`INT_MAX`) at parsing and rejects `2147483648` with an option-specific “Value too large for defined data type” error:

- `-N NUMBER`;
- `-l PAGE_LENGTH`;
- `--column COLUMN`.

Values up to `usize::MAX` are therefore not the compatibility domain merely because Rust can represent them.

### Derived geometry

Individual acceptance does not imply a valid combination. Examples using an empty input:

- `pr -l 2147483647 -3` parses the page length, then reports `integer overflow`;
- large page-length/column products can fail as derived geometry before any page contents are printed;
- `--column 2147483647` is individually accepted but can fail later with `page width too narrow` depending on the remaining layout.

### First-line-number behavior

GNU accepts `-N 2147483647`. Its display width can truncate the visible number, so tests must assert error/exit boundaries and appropriate output semantics rather than assuming a full-width decimal rendering.

## Candidate direction

A complete repair likely needs two layers.

### 1. Option-specific bounded parsing

Parse the affected GNU integer-domain options through a helper that:

- accepts `0..=i32::MAX` or the option's narrower valid range;
- distinguishes malformed input from positive overflow;
- emits the existing GNU-compatible option-specific diagnostic;
- handles the legacy `-COLUMN` operand consistently with `--column`.

### 2. Checked derived geometry

Centralize page-shape calculations and use checked operations for:

- content lines times columns;
- double-space adjustments;
- row/column table dimensions;
- page-number and line-number progress where the semantic domain can be exhausted.

A checked failure should return the GNU-compatible `integer overflow` error, not clamp or wrap.

## Required tests

At minimum:

1. `-N INT_MAX` accepted; `INT_MAX + 1` rejected without panic;
2. `-l INT_MAX + 1` rejected at input parsing;
3. `--column INT_MAX + 1` and legacy `-COLUMN` rejected;
4. individually accepted page length and column values whose product is invalid return `integer overflow`;
5. debug/overflow-check and release behavior agree;
6. ordinary pagination, merge, across, double-space, and no-header modes remain unchanged;
7. no test relies on actually allocating near the boundary.

## Stop signal

Do not write the source candidate until:

- every affected option's GNU maximum and diagnostic wording are mapped;
- the derived-geometry calculations are listed in one place;
- the product/error threshold is expressed semantically rather than inferred from host `usize`;
- legacy short-operand parsing is covered;
- tests can reach all boundaries without large allocation.

## Interpretation

The operation owner is the page geometry, not each arithmetic expression in isolation. Fixing only the two reported panic lines would leave other allocations and products exposed and could make debug and release builds disagree elsewhere.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other contact has been authorized or made.
