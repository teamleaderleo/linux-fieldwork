# Proxy signal mistaken for authoritative completion

## Metadata

```json
{
  "schema": 1,
  "id": "proxy-signal-for-authoritative-state",
  "kind": "bug-species",
  "maturity": "supported",
  "facets": {
    "domains": ["testing", "virtualization", "lifecycle"],
    "concerns": ["ordering", "state-consistency", "truthfulness"],
    "mechanisms": ["observation", "state-transition"],
    "triggers": ["asynchrony", "reuse"]
  },
  "aliases": ["correlated-symptom-as-completion"],
  "relations": [],
  "cases": ["teamleaderleo/linux-fieldwork#423"]
}
```

## In simple words

A test or controller observes a symptom that usually accompanies completion and then starts the next lifecycle step before the component that owns completion has actually said it is done.

```text
shutdown requested
→ SSH disappears
→ test reuses VM/disk
→ VMM shutdown may still be settling
```

## Hunt it

Find transitions followed by immediate reuse, delete/create, restart, or replacement. Ask what the transition owner emits at completion and compare that with what the caller currently waits for.

## Repair shape

Wait for the owner-issued terminal event/state. If no authoritative signal exists, add one at the owner boundary or prove that the existing proxy is ordered strongly enough to serve that role.

## Regression shape

Make the proxy happen early while deliberately delaying authoritative completion. The next lifecycle transition must remain blocked.

## Limits

A proxy is not inherently wrong. It becomes a bug only when its ordering is weaker than the property the caller assumes.

## Case

Linux Fieldwork #423 records the Cloud Hypervisor lifecycle test repair from SSH disappearance to the VMM-owned `shutdown` event.
