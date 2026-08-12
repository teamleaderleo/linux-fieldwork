LIVE CHECKPOINT

Unit: SquashFS v2/v3 inode fragment-index corruption boundary
Worker or variant: LF-R22 / recent hardening review
Exact head: plougher/squashfs-tools@5436ec0e5bf50dd8f7fe182d9ffd92b0861cb491
Question: Do the August v2/v3 fragment-index checks reject the first index beyond the allocated table?
Observed so far: no. Both use `fragment > sBlk.s.fragments` then index `fragment_table[fragment]`; the table has exactly `sBlk.s.fragments` entries. Current v4 uses `>=` as the passing control.
Changed paths: Fieldwork only — candidate.patch, repro.c, README.md, STATUS.md
Completed gates: current v2/v3 source; allocation/count proof; v4 control; August 3 introduction commits; upstream issue search; reduced boundary discriminator
Cleanup state: no archive/mount/namespace state created
Evidence boundary: exact source/history + reduced boundary model; no crafted-image ASan integration yet
Next safe action: sweep sibling recent corruption checks for count/index transcription mistakes; optional owned v2/v3 crafted-image ASan fixture
External-contact state: no upstream interaction authorized or made
