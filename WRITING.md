# Writing in Linux Fieldwork

## In simple words

Make the technical claim easy to see before the machinery around it. A reader should be able to recover the question, current behavior, consequence, evidence, limit, and next decision without excavating the whole investigation.

The repository has accumulated several useful reader-facing conventions over time: `## In simple words`, `## TL;DR`, `## Explain like I'm five`, and `## Why care`. Treat those as tools, not a ceremony. Use the headings that make this record easier to understand. A short investigation may need one compact opening passage. A complicated upstream packet may earn separate summary and consequence sections.

## Lead with the thing that is happening

For an investigation, begin with the concrete question or current answer.

> Does the cache publish a partial response after the origin closes early?

For a candidate:

> I propose delaying final-name publication until the complete declared response has arrived.

For a retained result:

> The candidate protects cache integrity, while the first client can still receive a partial HTTP 200 after headers have escaped.

Source paths, exact heads, and commands matter. They come after the reader knows what those details are proving.

## Explain the owner and the consequence

Name the operation owner. Say what receives the effect: file, process, socket, package database, allocator, VM, user, caller, later retry, or reviewer decision.

Prefer:

```text
origin promises 100 bytes
        ↓
sends 40, then EOF
        ↓
cache must discard the temporary entry
```

to several paragraphs saying response handling became more robust.

Use code, traces, state diagrams, shell transcripts, and tables when they make the mechanism obvious. Plain language means comprehensible, not non-technical.

## Keep evidence classes visible

Write current source behavior in present tense. Write completed execution in past tense. Write the candidate effect and remaining work in future tense.

Keep these separate when they differ:

- source says;
- executed evidence showed;
- interpretation suggests;
- the selected design chooses;
- a later experiment still has to establish.

Put caveats beside the claim they qualify. A reader should not have to reach `## Evidence boundary` to discover that the headline result came from one architecture or reduced fixture.

## Avoid template voice

A technical record can satisfy every field and still sound as if a form wrote it.

Skip stock announcements such as “The key insight is,” “This matters because,” “There are three reasons,” or “The following section explains” when the next sentence can simply state the mechanism or consequence. Do not manufacture groups of three, parallel paragraphs, or recap endings to make a report feel complete.

Contractions are fine. Semicolons are fine. One blunt sentence is fine. A long sentence is fine when the clauses genuinely belong together. Preserve the author's cadence while making the technical meaning exact.

Prefer concrete nouns and verbs. Words such as `robust`, `comprehensive`, `safe`, `clean`, `significant`, and `improved` need the specific property beside them.

Let a result end after it lands. The final section should add a decision, limit, reopen condition, or next action; it does not need to retell the investigation.

## Reader entry points

Use whichever of these earns its space:

- `## In simple words` — one compact technical explanation;
- `## TL;DR` — useful when the record is long or the disposition changes often;
- `## Why care` — useful when the consequence is easy to lose in implementation detail;
- `## Question` — useful when the answer is still genuinely open;
- a literal state trace, truth table, or before/after snippet — often better than another prose section.

`## Explain like I'm five` remains acceptable when that voice genuinely helps. It is no longer a required ritual for every investigation. Explain specialized terms once and then use the correct term.

## Revision

When the conclusion changes, update the opening explanation first. Do not leave a stale summary above correct evidence.

During a prose pass, protect the parts that already work. Fix the vague noun, canned transition, duplicated caveat, or padded ending instead of rewriting a useful report into a new house voice.

## Close with the decision

Before calling a durable record complete, make it easy to recover:

```text
What did we establish?
What remains outside the evidence?
What exact head or artifact carries the result?
What decision follows?
What would reopen it?
```

That is enough. The repository keeps the transcripts.
