# Upstream issue draft

Status: `NOT NEEDED`  
Proposed destination: canonical mmdebstrap repository  
External contact authorized: `false`

A direct source-plus-regression pull request is the preferred packet for this bounded defect. Keep the following text available if maintainers require an issue first.

## Proposed title

`tarfilter --idshift retains stale PAX uid/gid values`

## Draft

### Summary

`tarfilter --idshift` updates a member's integer uid and gid, while existing PAX `uid` and `gid` headers remain. For values that require PAX numeric encoding, those retained strings override the shifted fields when the output archive is read, so the command succeeds while preserving the original ownership.

### Observed behavior

Create a PAX archive with one regular member using uid `1000000000` and gid `1000000001`, then run:

```sh
python3 tarfilter --idshift=7 < input.tar > output.tar
```

Reading `output.tar` reports uid `1000000000` and gid `1000000001`. An ordinary control member using uid `1000` and gid `1001` reads back as `1007` and `1008`.

### Expected behavior

Both members carry identities shifted by seven. When shifted values require PAX representation, output PAX `uid` and `gid` values reflect the shifted integers.

### Minimal reproduction

```python
import io
import subprocess
import tarfile

source = io.BytesIO()
with tarfile.open(fileobj=source, mode="w", format=tarfile.PAX_FORMAT) as archive:
    member = tarfile.TarInfo("large")
    member.uid = 1_000_000_000
    member.gid = 1_000_000_001
    archive.addfile(member, io.BytesIO())

result = subprocess.run(
    ["python3", "tarfilter", "--idshift=7"],
    input=source.getvalue(),
    stdout=subprocess.PIPE,
    check=True,
)
with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:*") as archive:
    member = archive.next()
    print(member.uid, member.gid, member.pax_headers)
```

### Source analysis

The id-shift block increments `member.uid` and `member.gid`, then passes the same member and its retained `pax_headers` to `tarfile.addfile()`. Removing the stale numeric PAX keys after the validated shift lets Python serialize the new values using the appropriate ordinary or PAX representation.

### Evidence

The behavior was reproduced with Python 3.13.5. A focused regression distinguishes a large PAX member from an ordinary control, preserves payload and unrelated PAX metadata, and verifies an inverse-shift round trip.

### Compatibility and scope

The correction concerns numeric uid/gid metadata for active nonzero `--idshift`. It leaves names, paths, modes, timestamps, links, payloads, and unrelated PAX keys unchanged.

### Proposed direction

After successful negative-value validation and integer shifting, remove only `pax_headers["uid"]` and `pax_headers["gid"]`, then extend the existing `tests/tarfilter-idshift` test with a large-ID PAX case.

## Submission checklist

- [x] Current public issue and pull-request overlap rechecked on 2026-08-01; no indexed equivalent found.
- [x] Affected current upstream tarfilter revision confirmed.
- [x] Reproduction is minimal and safe.
- [x] No private credentials, internal-only links, or unsafe artifacts included in this draft.
- [x] Exact external destination identified.
- [ ] Current upstream candidate and native test completed.
- [ ] Explicit authorization recorded.
- [ ] Submitted public reference and timestamp recorded in the unit packet.
