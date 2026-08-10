# glibc ld.so.cache numeric comparator integer domain

State: `executing comparator gate`

Owning issue: #532  
External contact: `false — unauthorized`

## TL;DR

Current glibc's `_dl_cache_libcmp` parses arbitrary decimal runs into signed `int` and subtracts the resulting values. This investigation first executes the exact function body under ordinary optimization and UBSan, then only if warranted moves to generated-cache behavior.

Exact source: `gnutools/glibc@6288139c32a194e0005593c30af6c79bb698cdf2`, `elf/dl-cache.c::_dl_cache_libcmp`, checked 2026-08-10.

## First gate

`probe.sh` compiles the exact current comparator body twice:

- ordinary `-O2` to record pairwise signs and total-order checks for small controls plus decimal runs around the signed-32-bit boundary;
- UBSan with non-recovering signed-overflow handling to distinguish checked arithmetic from undefined signed arithmetic.

The probe uses only generated local source and binaries. It performs no loader-cache write, package install, privileged action, or external service call.

## Evidence boundary

A sanitizer result establishes an arithmetic defect in the exact comparator logic, not by itself an observable loader/cache lookup failure. An end-to-end private-cache matrix is a separate second gate and will be added only if this first result warrants it.
