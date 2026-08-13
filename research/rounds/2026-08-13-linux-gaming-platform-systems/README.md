# Linux gaming and platform systems scout — 2026-08-13

## In simple words

This round records a reusable set of Linux gaming, graphics, compositor, compatibility, input, audio, streaming, and performance projects worth scouting when we want a new systems question.

These are research surfaces. Future work should begin with source and test mapping, exact current revisions, and a bounded question. Promote only candidates that survive evidence.

## Primary scouting set

### Graphics translation and GPU behavior

- `doitsujin/dxvk` — Direct3D 8/9/10/11 to Vulkan; synchronization, descriptors, shaders, resource lifetime, performance, driver compatibility.
- `HansKristian-Work/vkd3d-proton` — Direct3D 12 to Vulkan; barriers, command queues, descriptors, shaders, ray tracing and presentation interactions.
- `mesa3d/mesa` — OpenGL/Vulkan drivers, shader compilers, winsys code, memory, synchronization and device-specific behavior.
- `baldurk/renderdoc` — graphics capture/replay, API interception, resource-state reconstruction and shader debugging.
- `KhronosGroup/SPIRV-Tools` — SPIR-V validation, optimization and transformation.
- `KhronosGroup/glslang` — GLSL/HLSL compilation and SPIR-V generation.
- `haasn/libplacebo` — Vulkan-based rendering, color management and video presentation.

### Compositors, display, input and desktop integration

- `ValveSoftware/gamescope` — Vulkan compositor, Wayland, DRM/KMS, HDR, frame pacing and display ownership.
- `swaywm/wlroots` — reusable Wayland compositor primitives, output lifecycle, DRM/KMS, input and rendering.
- `GNOME/mutter` — Wayland/X11 compositor, frame scheduling, input and display behavior.
- `KDE/kwin` — compositor/window manager, Wayland, DRM, presentation and color management.
- `emersion/libliftoff` — DRM/KMS plane allocation and composition decisions.
- `libinput/libinput` — Linux input devices, event processing, quirks, gestures and hotplug.
- `libsdl-org/SDL` — windowing, controllers, input, audio and platform backends used by games and emulators.
- `flightlessmango/MangoHud` — performance overlay and Vulkan/OpenGL telemetry.
- `DadSchoorse/vkBasalt` — Vulkan post-processing layer and effect injection.

### Compatibility and game runtime

- `ValveSoftware/Proton` — Linux game compatibility integration and runtime behavior.
- `wine-mirror/wine` — Windows API compatibility, processes, synchronization, graphics, input, filesystem and loader behavior.
- `FEX-Emu/FEX` — x86/x86-64 execution on ARM64 Linux; dynamic binary translation, JIT/code-cache lifetime, x86 memory ordering, signals, syscall/ABI translation, host-library forwarding, and Wine/Proton compatibility.
- `ValveSoftware/GameNetworkingSockets` — realtime networking, packet scheduling, reliable/unreliable delivery, P2P and encryption.
- `flatpak/flatpak` — desktop application sandbox and runtime integration.
- `containers/bubblewrap` — namespaces, mounts, sandbox setup and process boundaries relevant to launch/runtime behavior.
- `ostreedev/ostree` — image/update deployment useful for appliance-like gaming systems.

### Emulation and JIT-heavy systems

- `RPCS3/rpcs3` — PS3 emulation, PPU/SPU recompilation, RSX, timing, kernel and synchronization.
- `dolphin-emu/dolphin` — GameCube/Wii emulation, JITs, GPU backends, timing, audio, input and netplay.
- `xenia-project/xenia` — Xbox 360 CPU/GPU emulation and kernel behavior.
- `PCSX2/pcsx2` — PlayStation 2 recompilers, GS renderer, timing and compatibility.
- `PPSSPP/ppsspp` — PSP JIT, graphics translation, timing and portable platform behavior.
- `libretro/RetroArch` — frontend/runtime timing, input, audio/video synchronization and platform integration.

### Streaming, media and realtime I/O

- `LizardByte/Sunshine` — Linux game-streaming host, capture, encoding, input and latency.
- `moonlight-stream/moonlight-qt` — streaming client, decode, presentation, input and latency.
- `obsproject/obs-studio` — capture, GPU composition, encoding, plugins and audio/video synchronization.
- `FFmpeg/FFmpeg` — codecs, hardware acceleration, filters and media timing.
- `PipeWire/pipewire` — Linux realtime audio/video graph, buffers, devices and scheduling.
- `OpenALSoft/openal-soft` — spatial audio, mixing and backend behavior.

### Performance and native tooling

- `wolfpld/tracy` — low-overhead CPU/GPU profiling, sampling, unwinding and event transport.
- `ocornut/imgui` — immediate-mode UI used heavily in game and engine tooling.
- `llvm/llvm-project` — compiler/JIT/codegen/sanitizer work relevant to emulators and engines.
- `google/orbit` — native profiling and performance analysis.

## High-value cross-project questions

Prefer questions that can move between several projects:

- frame pacing, presentation timing and compositor ownership;
- Vulkan/D3D synchronization and resource lifetime;
- shader translation and backend equivalence;
- GPU memory pressure and allocation behavior;
- JIT/recompiler correctness, invalidation and code-cache lifetime;
- input hotplug, grabs, focus and event ownership;
- audio/video clock drift and realtime scheduling;
- process launch, cancellation, shutdown and descendant cleanup;
- sandbox/filesystem compatibility for game runtimes;
- capture/encode/decode latency and buffer lifetime;
- profiler overhead and measurement correctness;
- kernel/user-space boundaries in DRM, futex, scheduler, input and io_uring paths.

## Promotion rule

A project from this list becomes a formal target or investigation only after a scout identifies a concrete owner, exact source/test surface, reproducible discriminator and plausible consequence.

Keep broad reading here when the result is only orientation. Preserve negative results. Upstream contact requires a separate deliberate decision.
