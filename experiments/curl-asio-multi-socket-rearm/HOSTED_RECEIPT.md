# Hosted receipt — curl Asio re-arm discriminator

## Terminal hardened receipt

- Exact Linux Fieldwork head: `9a6a888c2b6b264e3179cc6b7cc2a0779534817e`
- Dedicated workflow run: `31012028751`
- Dedicated workflow conclusion: `success`
- Job: `discriminator`, ID `92326392927`, success
- Artifact ID: `8935333985`
- Artifact digest: `sha256:80c470be05c76e4d9c8c1706b36352117d73bdf02eaff29bdfc49ada43b36f1a`
- Linux Fieldwork CI run: `31012029493`, success

Every hardened step passed: credential-free checkout, exact environment capture, out-of-checkout compilation, two byte-identical runs, clean-checkout verification, build-staging removal, required artifact publication, and post-upload cleanup.

## Original hosted receipt

- Linux Fieldwork head: `a27240f35d2e08f42204d83119115d5f61cf65ee`
- Dedicated workflow run: `30759680701`
- Linux Fieldwork CI run: `30759680719`
- Dedicated workflow conclusion: `success`
- Repository CI conclusion: `success`
- Artifact ID: `8838935568`
- Artifact digest: `sha256:9a344ab1649b6c3135a01caf15bd7cc60ee4fcdeb3fa3fdf446bc2c67b659743`

## Hosted environment

The original receipt recorded:

- Runner OS: Ubuntu 24.04.4
- Runner image: `20260720.247.2`
- Kernel: `6.17.0-1020-azure`
- Boost development headers: 1.83
- libcurl development package: 8.5.0

The terminal hardened artifact retains the corresponding compiler, package, runner, kernel, source, and executable identities for run `31012028751`.

## Observed output

```text
one-shot: completed=0 timed_out=1 reads=1 body='hello '
rearm: completed=1 timed_out=0 reads=2 result=No error body='hello world!'
curl multi-socket Asio re-arm discriminator: PASS
```

## Classification

`PASS`

The hosted runs independently rebuilt the repository fixture and reproduced the local loopback result. The one-shot adapter consumed one readable completion and stalled with only `hello `. The generation-safe re-arm adapter received the second chunk and reached `CURLMSG_DONE` with `hello world!`.

## Review of the first hosted workflow

The first behavioral gate passed, but its workflow had evidence-quality gaps:

- moving `ubuntu-latest` runner;
- persisted checkout credentials;
- build output and receipt written into the checkout;
- one execution only;
- missing receipt tolerated with `if-no-files-found: warn`;
- incomplete compiler, curl, and Boost identity capture;
- no explicit post-upload cleanup proof.

Those gaps did not invalidate the behavioral result. The hardened workflow corrected every listed evidence gap and the terminal run `31012028751` passed all steps.

## Evidence boundary

This receipt proves the reduced local HTTP/1.1 split-response discriminator in the recorded hosted environments. It does not establish correctness for TLS, HTTP/2, `CURL_POLL_REMOVE`, deliberate cancellation, simultaneous read/write waits, connection reuse, curl-managed internal descriptors, or fd-number reuse.

## Authority

No curl, Ceph, or other canonical-project contact was made.
