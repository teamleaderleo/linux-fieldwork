# Reference observations

Observed locally with GNU tar 1.35 on 2026-07-30 using one archive member named `a/a/a/a`.

```text
expression     resulting member name
s/a/b/2        a/b/a/a
s/a/b/2g       a/b/b/b
s/a/b/g2       a/b/b/b
s/a/b/0        b/a/a/a
s/a/b/0g       b/b/b/b
s/a/b/00g      b/b/b/b
s/a/b/01       b/a/a/a
s/a/b/22       a/a/a/a
s/a/b/2g3      a/a/b/b
s/a/b/2i3      a/a/b/a
s/a/b/2r3      a/a/b/a
```

Interpretation used by the candidate:

- digits in one contiguous run form one decimal selector;
- selector zero uses the ordinary first/global start;
- `g` replaces from the selected match onward;
- without `g`, only the selected match changes;
- when multiple decimal runs occur, the last run controls the start;
- letter flags can appear before, after, or between decimal runs;
- match position is counted independently for each transformed archive field.

The executable regression carries the representative subset needed to distinguish each rule. The wider exploratory matrix remains here so later parser work can resume without reconstructing the original shell probe.
