# Acknowledge before required processing

## Metadata

```json
{
  "schema": 1,
  "id": "acknowledge-before-processing",
  "kind": "bug-species",
  "maturity": "supported",
  "facets": {
    "domains": ["distributed-systems", "controllers"],
    "concerns": ["recovery", "durability", "lifecycle"],
    "mechanisms": ["acknowledgement", "message-delivery", "replay"],
    "triggers": ["handler-failure", "interruption"]
  },
  "aliases": ["delete-before-handle", "premature-message-ack"],
  "relations": [],
  "cases": ["teamleaderleo/linux-fieldwork#517"]
}
```

## In simple words

A replayable message is acknowledged or deleted before the consumer has completed the work that acknowledgement is supposed to certify.

```text
receive replayable message
→ ACK / delete
→ required processing
→ processing fails
→ replay source already gone
```

## Hunt it

Read the queue/session contract first: what exactly does acknowledgement mean, and what causes redelivery? Then trace every fallible operation after acknowledgement. A particularly strong discriminator fails the first post-ack action and restarts the listener.

## Repair shape

Keep the message replayable until required processing reaches its durable/local completion boundary. If moving acknowledgement later creates duplicate delivery, define idempotency or exact message identity rather than trading recovery for silent loss.

## Regression shape

Compare baseline success, failure immediately before acknowledgement, failure immediately after acknowledgement, restart, and redelivery. Record acknowledgement count, handler calls, replay count, and final external/local state.

## Limits

This is **not** the same as losing an acknowledgement after an external mutation may already have committed. That sibling is an ambiguous-outcome problem and may require reconciliation rather than simply moving the acknowledgement later.

## Case

Linux Fieldwork #517 maps the `actions/scaleset` listener ordering and the replay semantics that make the question concrete.
