# Debug-utils pNext runtime evidence scope — 2026-08-14

One statement in `MAINTAINER_QUESTION_BANK.md` currently outruns the retained workflow evidence reviewed here.

Owned-FEX workflow `linux-fieldwork-vulkan-pnext-fix.yml` has two runs. Run `31737952681` failed while building FEX and skipped the probe. Run `31738785517` completed, but it applied both the native-first experiment and a separate debug-utils pNext-suppression candidate before running the zero-callback probe.

The successful run records:

```text
PNEXT_ZERO_CREATE result=0 instance=<non-null> callback_count=0
```

That directly demonstrates candidate sufficiency: explicit handling of the embedded debug-utils create-info can make the hosted ARM64 probe return with no guest callback delivery.

It does not, by itself, establish the currently stated `baseline=132` and `native-first-only=132` runtime pair because neither unsanitized variant was executed by the successful workflow. The failed first run cannot provide that evidence because its probe never ran.

The source-level sibling finding remains strong: current `vkCreateInstance` handles debug-report create-info specially but does not equivalently handle `VkDebugUtilsMessengerCreateInfoEXT`, and the ordinary standalone debug-utils creation wrapper does not own this embedded path.

Until an unsanitized ARM64 matrix is retained, treat the 132/132 pair as a source-supported expectation rather than verified runtime evidence. The successful suppression run remains valid design evidence.

FEX upstream remained read-only.
