# Self-review checklist

## Archive evidence

- Unsafe absolute and parent-traversal member paths fail closed.
- Link targets remain byte-for-byte semantic data.
- Numeric ownership, modes, file types, devices, PAX extras, timestamps, sizes, content hashes, and archive order are represented.
- Duplicate normalized member paths fail closed.
- Comparisons distinguish absence from JSON `null`.
- Noise fields are ignored only by explicit request.

## Host evidence

- Default context output omits hostname and account names.
- Full subordinate-ID files and mount information require `--include-sensitive`.
- Failed namespace or mount probes are retained with exit status instead of aborting the report.

## Debian report evidence

- Download size has a hard limit.
- Raw mbox bytes receive a SHA-256 digest.
- Message bodies receive individual digests.
- The summary records message metadata and referenced URLs without retaining body text.
- Raw mail remains a temporary artifact pending review.

## Reproduction logic

- Source identity and test-entrypoint hashes are recorded before execution.
- APT policy and package versions are captured before and after the test.
- The full shared-mirror test runs before single-case reduction.
- Timeout, failure, pass, and neutral results remain distinct.
- Current sid and report-matched historical reproduction are described as different claims.
- No patch is proposed before the first failing operation identifies an owner.

## Repository integration

- The investigation links to LF-02 and LF-14.
- The `mmdebstrap` target map links back to the investigation.
- Existing programme, target, research, and investigation conventions stay intact.
- Upstream contact remains unauthorized.
