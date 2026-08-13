# Thunk-config fixture correction — 2026-08-14

This note corrects one conclusion in `NINTH_PASS_FAULT_AND_CONSUMER.md`. It does not rewrite that historical review in place.

## Correction

The ninth-pass note treated this hosted configuration as a disqualifying harness defect:

```text
FEX_THUNKCONFIG=<install>/share/fex-emu/ThunksDB.json
Config.json: "ThunkConfig": "<install>/share/fex-emu/ThunksDB.json"
Config.json: "ThunksDB": {"Vulkan": 1}
```

That conclusion was too strong.

FEX's configuration documentation defines `FEX_THUNKCONFIG` / JSON `ThunkConfig` as the path to a thunk-config JSON file. The library-forwarding documentation also identifies the installed `$prefix/share/fex-emu/ThunksDB.json` as FEX's provided thunk mapping database:

- https://wiki.fex-emu.com/index.php/Config
- https://wiki.fex-emu.com/index.php/Development%3ASetting_up_Thunks

The exact reviewed source `71afe476751deac24adabd1adb575fd2337b6e0a` additionally keeps database loading separate: `FileManager::LoadThunkDatabase()` reads `GetConfigDirectory(Global) + "ThunksDB.json"` and consumes its `DB` object. The hosted workflow's `Config.json` independently enables the Vulkan thunk through its `ThunksDB` section.

Therefore the presence of `FEX_THUNKCONFIG=<installed ThunksDB.json>` does **not** establish that the callback probes used the wrong host/guest thunk database, nor does it justify discarding a run whose guest probe body demonstrably executed. At worst this is a redundant/non-minimal configuration choice relative to FEX's smaller CI enablement files; it is not evidence that the observed dynamic callback differential is a configuration artifact.

## Consequence for retained runtime evidence

Owned-FEX Actions run `31736419480` remains usable runtime evidence, subject to its ordinary probe boundaries:

```text
baseline:
  direct-report=0
  direct-utils=0
  dynamic-report=132
  dynamic-utils=132
  procaddr=20

candidate:
  direct-report=0
  direct-utils=0
  dynamic-report=0
  dynamic-utils=0
  procaddr=0
```

The correct fixture questions for that run are whether the x86 probe body ran, whether the intended guest and host Vulkan thunks loaded, whether the X11 constructor prerequisites were present, and whether baseline/candidate differed only by the recorded diagnostic source change. The earlier repaired-rootfs receipts and the run's own logs provide those discriminators.

## What remains true from the ninth pass

The older hosted runs that died before useful callback markers remain non-evidence for Finding A. Missing X11 guest symbols were a real fixture failure in that earlier minimal rootfs. The correction here is narrow: `FEX_THUNKCONFIG` pointing at the installed `ThunksDB.json` is not, by itself, a reason to reject the later successful differential.

FEX upstream remained read-only throughout this review.
