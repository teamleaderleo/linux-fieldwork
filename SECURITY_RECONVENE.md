# Security reconvene triage

## In simple words

Linux Fieldwork is not a vulnerability-hunting programme. Most security-adjacent findings should stay in the ordinary investigation workflow: reproduce them safely, repair them, test the boundary, and keep moving.

`RECONVENE` is the all-red signal for the uncommon case where a result starts to look like a serious vulnerability or disclosure event. Use it early enough to avoid putting enabling detail or raw evidence into a public issue, pull request, log, or chat.

## Continue normally

Keep working when the result remains local, synthetic, owned, disposable, and straightforward to describe publicly. Typical examples include:

- path, permission, malformed-input, cleanup, signal, or wrong-result defects;
- defense-in-depth fixes with restrictive prerequisites;
- crashes or corruption reproduced only in a disposable fixture;
- analysis of already-public CVEs, advisories, patches, or source changes;
- a bounded candidate repair that does not require live-target validation.

Security vocabulary alone is not a reason to stop. Do not use a numeric severity score as the decision rule.

## All-red signals

Switch to `RECONVENE` when the evidence begins to support one or more of these:

- unauthenticated or pre-auth compromise with little user interaction;
- wormable or self-propagating behavior;
- broad default reach across widely deployed Linux, package, service, container, kernel, or supply-chain infrastructure;
- reliable remote code execution, sandbox or container escape, cross-tenant access, or equivalent authority gain;
- a new exploit path or variant that is not already public in substance;
- active exploitation, credible mass exploitation, or unusually low-friction reproduction against real deployments;
- continuing would require a live target, destructive action, persistence, stealth, credential use, or production-changing behavior;
- the useful next evidence cannot safely be committed to this public repository.

These are prompts for judgment, not a checklist that must be fully satisfied. A foreboding combination of reach, reliability, authority gain, and publication risk is enough.

## What to do

1. Stop deepening exploitability, target reach, payload behavior, or operational detail.
2. Preserve only a public-safe checkpoint in the ordinary repository surface.
3. Record the exact head, affected component, broad finding class, first distinguishing result, cleanup state, evidence boundary, and decision needed.
4. Do not paste raw logs, crash material, target identifiers, or reproduction detail that materially enables abuse.
5. Finish safe cleanup and confirm no process, service, mount, credential, or modified external state remains.
6. Ask for one decision: continue with a sanitized synthetic reduction, move to an explicitly authorized private handling surface, prepare coordinated upstream contact, or stop and retain the result.

Use the `RECONVENE CHECKPOINT` in [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md).

## Good-citizen rule

The goal is not to maximize severity, claim a CVE, or prove every possible consequence. The goal is to notice when ordinary engineering work may have crossed into a disclosure-sensitive result, stop before public overexposure, and let a human choose the appropriate next surface.

Public-source review, defensive repair, and ordinary CVE study remain allowed. Reconvening changes the coordination and publication boundary; it does not erase valid evidence or turn every security bug into an emergency.
