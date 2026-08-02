# Safetensors s390x `TensorSpec` byte-order boundary

State: `SOURCE-MAPPED — TARGET EXECUTION NOT MATERIALIZED`  
Worker or variant: `LF-R02`  
Public contact authorized: `false`

## Bounded question

Is safetensors issue `#812` a concurrent serialization defect, or does the low-level `TensorSpec` API serialize native big-endian bytes without the conversion performed by the high-level NumPy API?

## Exact source state

| Item | Value |
| --- | --- |
| Repository | `safetensors/safetensors` |
| Inspected head | `6eb4dc9a28ebce297606e0f4836bbf28839cacef` |
| Python Rust binding | `bindings/python/src/lib.rs` |
| Binding blob | source inspected at exact head |
| NumPy wrapper | `bindings/python/py_src/safetensors/numpy.py` |
| NumPy wrapper blob | `75178ed773f455b87d2f9099806cb21087c5a9c7` |
| Failing test | `bindings/python/tests/test_threadable.py` |
| Test blob | `97d4229bf4380b9d3cec1d74197dd4f0b419fb95` |
| Public issue | `safetensors/safetensors#812` |
| Equivalent PR found | none by issue-number search |

## Observed boundary

The high-level NumPy save path calls `_is_little_endian()`. For a native big-endian array, it creates a byteswapped copy, retains that copy, and passes its pointer to `TensorSpec`.

The low-level `TensorSpec` implementation:

- stores `dtype`, shape, raw pointer, and byte length;
- exposes the pointed-to memory as an unmodified borrowed byte slice;
- releases the GIL while the core serializer writes those bytes;
- documents pointer lifetime as the caller's responsibility;
- does not document or encode the buffer byte order.

The s390x test constructs `TensorSpec` directly from native NumPy pointers. It therefore bypasses the high-level byte-swap path. The reported result—`int8` survives while `float32` is byte-corrupted—is consistent with raw native-endian bytes being written as little-endian format data.

This is an inference from current source and the public transcript. It is not yet a target-executed result.

## Required discriminator matrix

Run on s390x, preferably both native Fedora infrastructure and qemu-user:

1. direct `TensorSpec`, one thread, native `float32`;
2. direct `TensorSpec`, four threads, native `float32`;
3. direct `TensorSpec`, one and four threads, explicit little-endian/byteswapped `float32`;
4. `safetensors.numpy.save_file`, one and four threads;
5. `int8` controls for all paths;
6. a non-native explicit little-endian NumPy dtype control;
7. serialized byte inspection for one known `float32` value.

Interpretation:

- single-thread and multi-thread direct failures with wrapper success: byte-order contract boundary, not concurrency;
- only multi-thread failures after correct byte order: concurrency or lifetime defect;
- wrapper failure: high-level endian conversion or retention defect;
- different bytes across identical runs: broader serializer nondeterminism.

## Candidate decisions

Possible outcomes are deliberately separated:

- document `TensorSpec` as requiring little-endian format bytes and fix the test;
- add explicit byte-order information and conversion to the low-level API;
- replace raw-pointer construction with a buffer object that retains ownership and exposes format metadata;
- keep the low-level contract unchanged while adding a safe NumPy-facing concurrent serialization helper.

A correction must not silently copy all low-level buffers without an explicit API and performance decision.

## Capability boundary

No controlled safetensors fork was found in the connected inventory used in this pass. No source branch or Actions run has been created. The first executable work requires a controlled fork or another explicitly owned target-execution repository.

## Authority

Public source and issue reading plus internal Fieldwork documentation are authorized. No public comment, issue, pull request, review, reaction, or email has occurred.
