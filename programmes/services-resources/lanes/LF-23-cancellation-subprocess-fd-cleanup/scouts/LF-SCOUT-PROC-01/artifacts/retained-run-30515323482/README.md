# Retained LF-23 CI evidence

This directory retains the compact evidence set from GitHub Actions run `30515323482`, job `90783738451`, against branch commit `72506f958aa2cc2555cc51cac19d057cb88e5c30`.

The complete uploaded artifact was `lf-23-cancellation-evidence-30515323482-1`, artifact ID `8748644983`, with GitHub digest `sha256:6387c76da15c9a9425cf0270c42a55d99e1a60fca7c9a548e035649566ec2b40`. GitHub retains that archive for 14 days. This directory keeps the durable inputs, outcome summary, exact checkpoints, logs, and compact resource observations needed to audit the report after the archive expires.

Files:

- `environment.json` — kernel, container userspace, tool versions, and privilege identity.
- `source.json` — imported source path, byte count, and SHA-256.
- `summary.json` — exact harness result object.
- `checkpoints.tsv` — raw checkpoint rows with PID, parent PID, process group, root, and open descriptors.
- `combined-stderr.log` — interrupted and clean-rerun stderr for every case.
- `resource-summary.json` — PIDs, locks, Unix sockets, and target mounts before the signal, shortly after it, and after exit.

The full workflow artifact additionally contained per-process `/proc/<pid>/status`, descriptor maps, complete mountinfo, full `/proc/locks`, complete `ss -ap` output, command records, stdout, temporary instrumented source copies, and per-case result files.
