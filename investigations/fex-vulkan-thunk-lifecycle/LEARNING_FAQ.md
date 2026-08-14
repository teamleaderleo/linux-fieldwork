# FEX Vulkan learning FAQ

This is the beginner-facing companion to the technical evidence in this investigation. It is meant to make the FEX/Vulkan work readable before diving into `ThunkLibs/libvulkan/Host.cpp`, `Guest.cpp`, generated thunk code, and the deeper unload/reload lifetime work.

It is a **learning guide, not a substitute for the evidence receipts**. Exact claims, revisions, CI runs, artifacts, controls, and current design status live in the investigation records.

## The one-sentence picture

We are running x86-64 software through FEX on an ARM64 Linux guest, then crossing from that translated x86-64 world into native ARM64 Vulkan libraries. Function pointers and callbacks make this boundary bidirectional, so FEX has to adapt both calls into native code and calls back toward guest code.

## Why are x86-64 and ARM64 different worlds?

A compiled program eventually becomes machine instructions. x86-64 CPUs and ARM64 CPUs assign different meanings to instruction bytes and use different machine-level calling conventions.

Conceptually:

```text
x86-64 application code
        ↓
      FEX
        ↓
ARM64 machine code
```

A function address that points at x86-64 instructions cannot simply be handed to native ARM64 code and executed directly. If native ARM64 code jumps into an x86-64 instruction stream, the CPU can encounter an invalid ARM64 instruction and raise `SIGILL` (illegal instruction).

## What is FEX doing?

FEX is a userspace x86/x86-64 emulator for ARM64 Linux. It dynamically translates guest x86-64 execution into host ARM64 execution and also has to bridge operating-system and library boundaries.

For this investigation, the interesting path is approximately:

```text
x86-64 program
    ↓
FEX guest execution
    ↓
FEX Vulkan guest thunk
    ↓
FEX host thunk / native call boundary
    ↓
native ARM64 Vulkan loader / driver
```

The eventual gaming stack may contain Wine/Proton and graphics translation above this, but `vulkaninfo` is useful because it removes many unrelated layers while preserving the x86-64 → FEX → ARM64 Vulkan boundary.

## What is Vulkan?

Vulkan is a low-level graphics API. Applications use it to create instances and devices, enumerate hardware, allocate resources, submit work, synchronize, present images, and query optional functionality.

There is usually a Vulkan loader between an application and the actual driver:

```text
application
    ↓
Vulkan loader
    ↓
driver / ICD
    ↓
GPU
```

Vulkan also exposes many commands dynamically through function pointers.

## What is a function pointer?

A function pointer is a value representing a callable function. At the machine level, the key piece is an address where executable code begins, plus an expected calling signature.

Very simplified:

```text
function pointer
    ↓
address 0x12345678
    ↓
machine code for someFunction()
```

This is especially important in an emulator because the address may refer to code for a different instruction set or may require an adapter before the caller can use it.

## What is an ABI?

ABI means **Application Binary Interface**. It is the machine-level agreement between compiled pieces of code.

An ABI answers questions such as:

- Which registers carry arguments?
- Where does the return value go?
- How is the stack aligned?
- How are structures passed?
- Who preserves particular registers?

Two source functions can look identical in C or C++ while their machine-level call sequences differ across architectures.

That is one reason FEX needs thunk machinery instead of simply passing every pointer through unchanged.

## What is a thunk?

A thunk is adapter code that lets one calling world reach another.

For this investigation, the useful cartoon is:

```text
x86-64 application
      ↓
guest-side Vulkan thunk
      ↓
pack / translate / bridge
      ↓
host-side Vulkan thunk
      ↓
native ARM64 Vulkan
```

The exact implementation is more sophisticated, but the word `thunk` can be read as "little bridge/adaptor around a call."

## What are `Guest.cpp` and `Host.cpp`?

The relevant FEX Vulkan source is centered around:

```text
ThunkLibs/libvulkan/Guest.cpp
ThunkLibs/libvulkan/Host.cpp
ThunkLibs/libvulkan/libvulkan_interface.cpp
```

A useful first mental model is:

- `Guest.cpp`: behavior visible from the translated x86-64 guest side, including making dynamically returned native functions callable from guest code.
- `Host.cpp`: host-side Vulkan handling, including handwritten custom implementations for functions that need special treatment.
- `libvulkan_interface.cpp`: interface and thunk-generation metadata that helps define which Vulkan functions exist and which receive special handling.

When reading any line, keep asking: **which architecture owns this value right now?**

## What is `vkGetInstanceProcAddr`?

`vkGetInstanceProcAddr()` is Vulkan's dynamic function lookup for instance-level commands. It is often shortened to **GIPA**.

Conceptually:

```text
application:
"give me the function named vkCreateDebugReportCallbackEXT"

Vulkan:
"here is its function pointer"
```

If a command is unavailable, Vulkan can return a null pointer.

There is also `vkGetDeviceProcAddr()` (GDPA) for device-level commands.

## Why is GIPA special under FEX?

Native Vulkan returns a function pointer meaningful to native ARM64 code, while the application consuming it is x86-64 guest code.

So FEX needs machinery that makes the native function callable from the guest world. Dynamic Vulkan PFNs therefore cross a more complicated path than an ordinary directly linked guest function.

This same mechanism later becomes important in the unload/reload lifetime investigation.

## What is a callback?

A callback reverses the direction of a call.

Normal direction:

```text
application
    ↓
Vulkan
```

Callback direction:

```text
Vulkan
    ↓
application-provided function
```

An application may hand Vulkan a function pointer and ask Vulkan to call it later when some event occurs.

## Why are callbacks dangerous across x86-64 and ARM64?

Suppose an x86-64 application gives Vulkan this:

```text
pfnCallback = address of x86-64 callback code
```

If native ARM64 Vulkan receives that raw address and calls it directly:

```text
ARM64 Vulkan
    ↓
raw x86-64 callback address
    ↓
ARM64 CPU tries to execute x86-64 bytes
    ↓
SIGILL
```

A cross-ISA callback therefore needs translation, replacement, suppression, or another deliberate policy.

## What policy did FEX already have for debug callbacks?

FEX already had handwritten handling for legacy Vulkan debug callbacks. For `VK_EXT_debug_report`, FEX's custom create function copies/adapts the callback create information and substitutes a native dummy callback instead of passing the guest x86-64 callback directly to native Vulkan.

In plain English:

```text
guest asks Vulkan to use x86 callback
        ↓
FEX custom wrapper
        ↓
replace unsafe callback with native-safe dummy
        ↓
native Vulkan
```

This suppresses the real guest debug callback, but it follows an existing compatibility policy in FEX and avoids an invalid cross-ISA callback jump.

## What was Finding A?

Finding A is a routing mismatch.

FEX already had the callback-safe custom implementation, and one direct path could reach it. Dynamic lookup through `vkGetInstanceProcAddr()` could miss that custom implementation and continue through the generic dynamic-function path.

The bad path is approximately:

```text
x86-64 program
    ↓
vkGetInstanceProcAddr("vkCreateDebugReportCallbackEXT")
    ↓
FEX custom-function lookup misses the callback-safe implementation
    ↓
generic dynamic-function route
    ↓
native callback-creating Vulkan function
    ↓
raw guest callback reaches native ARM64 Vulkan
    ↓
callback fires
    ↓
ARM64 execution enters x86-64 callback bytes
    ↓
SIGILL
```

The direct-vs-dynamic discriminator was especially useful because it compared two routes to the same conceptual Vulkan operation.

## What did the diagnostic candidate change?

At the conceptual level, the candidate teaches the dynamic lookup path to recognize callback-sensitive functions and select FEX's existing custom implementation.

Then the path becomes:

```text
GIPA asks for callback-sensitive function
    ↓
FEX recognizes that this function needs custom handling
    ↓
FEX callback-safe wrapper
    ↓
unsafe guest callback is replaced/suppressed
    ↓
native Vulkan
```

The focused A/B changed the failing dynamic route to a clean route and was widened to cover both debug-report and debug-utils callback creation cases.

## Why is "native-first" lookup important?

There is an API-contract nuance.

Suppose the underlying Vulkan implementation does not expose some extension command. Native `vkGetInstanceProcAddr()` should be allowed to report that by returning a null pointer.

FEX should not accidentally make an unavailable Vulkan extension look available merely because FEX has a custom wrapper with that name.

The refined logic is therefore:

```text
1. Ask native Vulkan whether the proc exists.
2. If native Vulkan says "no" (null), preserve that result.
3. If it exists, check whether FEX needs a custom safe implementation.
4. Return the FEX custom implementation when needed.
5. Otherwise continue through the ordinary dynamic-function path.
```

This preserves native Vulkan availability semantics while still applying FEX's special callback policy.

## Why did another crash appear after Finding A was repaired?

The first crash happened during callback routing. After that boundary was crossed, `vulkaninfo` advanced through enumeration and later hit a different teardown/lifetime failure.

Think of two locked doors:

```text
Door A: callback routing
Door B: thunk lifetime during unload/reload
```

Repairing Door A exposes Door B. Door B does not invalidate the Door A result.

The lifetime lane later became a much larger investigation involving dynamic PFNs, hidden guest dependencies, cache retirement, unload/reload generation identity, callbacks, and resident bridge designs.

## What is `SIGILL`?

`SIGILL` is a Unix signal for an illegal instruction. In this investigation it is a useful symptom of native ARM64 execution reaching bytes that are not valid for the expected ARM64 instruction stream.

The signal alone does not prove the whole mechanism. The causal case comes from combining the signal with source mapping, the direct/GIPA differential, instrumentation, and the targeted routing change.

## What is `SIGSEGV`?

`SIGSEGV` is a segmentation fault signal. It usually means execution or memory access reached an invalid mapping or violated memory access rules.

The later FEX teardown work involves guest code being unloaded while FEX-owned execution paths can retain dependencies on that old guest generation. That is a separate lifetime problem from Finding A's cross-ISA callback routing.

# C++ basics for this source walk

The goal is to learn C++ as each construct appears in real FEX code. This section is a reference, not homework to memorize.

## What is a type?

C++ values have types.

Examples:

```cpp
int count = 3;
bool enabled = true;
```

`int` means integer. `bool` means true/false.

Vulkan defines many API-specific types such as `VkInstance`, `VkResult`, and function-pointer types beginning with `PFN_`.

## What is a variable?

A variable is a named value.

```cpp
int count = 3;
```

Read it as:

```text
create an integer named count and give it the value 3
```

## What does `auto` mean?

`auto` asks the compiler to infer the type from the value being assigned.

```cpp
auto result = SomeFunction();
```

Read it as:

```text
call SomeFunction, let the compiler determine the exact result type,
and store it in a variable named result
```

## What does `const` mean?

`const` means a value should not be modified through that name/reference.

It appears in many forms in C++, so interpret it in context. At beginner level, read it as a compiler-enforced promise about immutability.

## What does `if` mean?

```cpp
if (condition) {
  do_something();
}
```

Read:

```text
if condition is true, execute the code inside the braces
```

`else` gives the alternate branch.

## What does `==` mean?

Comparison for equality.

```cpp
if (name == "foo") {
  ...
}
```

Read:

```text
if name equals "foo"
```

## What do braces mean?

```cpp
{
  ...
}
```

Braces group statements into a block, such as the body of an `if`, function, loop, class, or namespace.

## What does `return` mean?

A function can produce a result for its caller.

```cpp
int double_it(int x) {
  return x * 2;
}
```

The function accepts an integer and returns an integer.

## Why do C++ statements end in `;`?

The semicolon terminates many C++ statements:

```cpp
DoThing();
int x = 4;
return value;
```

## What is a pointer?

A pointer stores an address.

```cpp
int x = 5;
int* p = &x;
```

Here:

- `x` is an integer.
- `&x` means "the address of x."
- `p` stores that address.
- `int*` means "pointer to an integer."

## What does dereferencing mean?

If `p` points to an integer, then:

```cpp
*p
```

means:

```text
access the integer stored at the address in p
```

The `*` symbol has several roles in C++, so always read it in context.

## What is `nullptr`?

`nullptr` is C++'s explicit null-pointer value.

Read it as:

```text
there is no valid object/function pointer here
```

This is important for Vulkan proc lookup because a null return can mean that a command is unavailable.

## What is a `struct`?

A `struct` bundles named fields.

```cpp
struct Example {
  int count;
  void* user_data;
};
```

Think of it as a form with named boxes.

Vulkan APIs use many structures, including structures containing function pointers such as callbacks.

## What does `.` mean?

Member access on an object:

```cpp
thing.member
```

Read:

```text
the member named member inside thing
```

## What does `->` mean?

Member access through a pointer:

```cpp
thing_ptr->member
```

Conceptually this is shorthand for:

```cpp
(*thing_ptr).member
```

Systems C++ uses `->` constantly.

## What does `::` mean?

`::` is the scope-resolution operator.

Examples:

```cpp
std::string
SomeClass::SomeFunction
```

Read it approximately as "inside/belonging to this namespace or class."

## What is `std::`?

`std` is the C++ standard-library namespace. Things such as `std::string`, `std::string_view`, containers, algorithms, and utilities live there.

## What is a string literal?

```cpp
"vkCreateDebugReportCallbackEXT"
```

is text embedded directly in the program.

## What is the `sv` suffix?

Code may use:

```cpp
"vkCreateDebugReportCallbackEXT"sv
```

The `sv` suffix creates a `std::string_view` literal.

A string view is a lightweight view over a sequence of characters. For this investigation, read the expression as "this function name as a string-like comparison value."

## What is a function declaration/signature?

```cpp
int add(int a, int b)
```

means:

```text
function name: add
inputs: two integers
return type: integer
```

The signature is important for function pointers and ABI adaptation because callers and callees need to agree on arguments and return values.

## What does `PFN_...` mean in Vulkan?

Vulkan uses many names beginning with `PFN_` for function-pointer types.

For example:

```cpp
PFN_vkVoidFunction
```

can be read as a generic Vulkan function-pointer type. `vkGetInstanceProcAddr()` needs a generic function-pointer return because it can return many different Vulkan commands.

## What is a cast?

A cast tells C++ to treat or convert a value as another type.

You may see old-style syntax:

```cpp
(PFN_vkVoidFunction)some_function
```

or C++-style casts such as:

```cpp
reinterpret_cast<SomeType>(value)
static_cast<SomeType>(value)
```

The exact meaning depends on the cast. In function-pointer routing code, a cast may convert a specifically typed function pointer into the generic Vulkan function-pointer type expected by the lookup API.

## What is `using`?

A type alias:

```cpp
using Callback = void (*)(int);
```

Read:

```text
Callback is another name for this function-pointer type
```

## What is `extern "C"`?

C++ normally encodes extra type/name information into compiled symbol names. `extern "C"` asks for C-compatible linkage for a declaration.

This is common around C APIs and interoperability boundaries.

## What is a namespace?

A namespace groups names so projects can avoid collisions.

```cpp
namespace Example {
  void Run();
}
```

Then the function can be named as:

```cpp
Example::Run()
```

## What is a template?

A C++ template describes code parameterized by a type or value.

Very simplified:

```cpp
template<typename T>
T identity(T value) {
  return value;
}
```

The compiler can create concrete versions for different `T`s.

FEX uses templates heavily in generated thunk and call-bridge code. We will unpack them token by token when we reach them instead of trying to learn template metaprogramming first.

## What are references (`&`) in declarations?

C++ references let a function or variable refer to an existing object without copying it.

```cpp
void inspect(const Thing& thing);
```

Read approximately:

```text
inspect receives a reference to an existing Thing and promises not to modify it through this reference
```

The `&` symbol also means "address-of" in expressions, so context matters.

## What should I ignore on the first pass?

On the first source walk, avoid getting trapped in every include, macro, generated symbol name, template helper, build-system detail, or style choice.

Track the semantic chain first:

```text
requested Vulkan function name
    ↓
native availability
    ↓
custom FEX routing decision
    ↓
which function pointer is returned
    ↓
which callback pointer native Vulkan eventually receives
```

Once that chain is clear, return to the syntax and supporting machinery.

# Finding A reading map

The first code-reading pass should proceed in this order.

## Group 1 — top of `Host.cpp`

Learn:

- `#include`
- namespaces
- `using`
- file-local helpers

Question to keep asking: which declarations come from Vulkan, which come from FEX, and which are local helpers?

## Group 2 — callback helpers

Find the dummy/debug callback helper and understand its signature.

Learn:

- function return types
- argument lists
- Vulkan callback types
- linkage where relevant

Goal: understand why this function is safe for native ARM64 Vulkan to invoke.

## Group 3 — custom `vkCreateDebugReportCallbackEXT`

Learn:

- Vulkan create-info structs
- pointers to structs
- copying/modifying a local structure
- member access
- replacing `pfnCallback`
- calling the real native Vulkan command

Goal: be able to explain exactly where the unsafe guest callback is removed from the host-facing data.

## Group 4 — `LookupCustomVulkanFunction`

Learn:

- `std::string_view`
- `if` / `else if`
- function names as data
- function pointers
- casts to `PFN_vkVoidFunction`

Goal: explain how a requested function name is mapped to a special FEX implementation.

## Group 5 — host `vkGetInstanceProcAddr`

Learn:

- native function lookup
- `nullptr`
- ordering of checks
- why native availability and FEX substitution are separate decisions

Goal: explain the native-first rule in source code instead of only in prose.

## Group 6 — `Guest.cpp`

Follow what happens when the guest receives a native Vulkan PFN.

Learn:

- `auto`
- maps/lookups
- helper functions
- `MakeGuestCallable`
- `LinkAddressToFunction`
- the idea of a synthetic guest-callable bridge around a native address

Goal: understand why a native ARM64 function address cannot simply be executed as x86-64 code.

## Group 7 — candidate delta

Read the smallest source delta and explain every token and every branch.

Goal: answer both:

1. Why does this eliminate the observed callback-routing SIGILL?
2. Which Vulkan semantics could a naive version accidentally change?

# Questions to be able to answer before proposing Finding A upstream

1. What is a function pointer?
2. What is an ABI?
3. Why can native ARM64 Vulkan not directly call an x86-64 callback pointer?
4. What is a FEX thunk?
5. What is GIPA?
6. Why are dynamically returned Vulkan PFNs special under FEX?
7. What existing FEX policy handles `VK_EXT_debug_report` callbacks?
8. What exact route bypassed that policy?
9. Why did the bad route produce `SIGILL`?
10. What did the direct-vs-GIPA A/B prove?
11. Why is checking native Vulkan availability before custom substitution important?
12. What does `nullptr` mean in this API contract?
13. Why does the later teardown `SIGSEGV` belong to a different finding?
14. Which parts of the final source change are behavior changes and which are type/cast plumbing?
15. What focused regression test would fail before the change and pass after it?

If these answers can be explained comfortably without memorizing wording, the source review has turned into genuine understanding.

# Current evidence boundary

This FAQ intentionally simplifies implementation details and uses cartoons. The investigation records carry the exact runtime claims.

Finding A is the cleanest teaching entry point because it connects a straightforward architecture fact — an ARM64 caller cannot execute a raw x86-64 callback — to a small, inspectable routing decision in FEX.

The unload/reload lifetime work is broader. It introduces hidden guest dependencies behind native PFNs, compiled lookup-cache state, load-generation identity, callback-trampoline ownership, in-flight execution, and resident bridge designs. Those topics should be learned after Finding A's source path is comfortable.

## Next lesson

Open current upstream FEX `ThunkLibs/libvulkan/Host.cpp` and begin at the top of the file. Read it in semantic groups, pausing on every new C++ construct as it becomes relevant. The immediate objective is to reach the custom debug callback implementation and `LookupCustomVulkanFunction()` with every line translated into ordinary English.
