# Why this candidate is incremental

PR #68 already retains the reviewed parser, sed-style replacement function, scope flags, hard-link/symlink handling, and PAX metadata cleanup. Repeating that full patch would create two competing integrated candidates.

This issue changes one concept: choosing which regex match receives the existing replacement function. Keeping it as a second patch makes the predecessor failure executable and lets a reviewer inspect the numeric delta without rereading the entire transform implementation.
