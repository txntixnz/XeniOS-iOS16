# Patch notes / test history

## Baseline

Device used for field testing: iPhone 13 Pro Max (`iPhone14,3`) on iOS 16.0 (`20A362`), installed with TrollStore on a Dopamine jailbreak.

### Original failure

The unmodified IPA terminated in dyld before executing XeniOS code because it was built for iOS 18 and imported runtime/framework symbols unavailable on iOS 16.

## T1 — deployment target + `quick_exit`

- Lowered app/Mach-O deployment target to iOS 16.0.
- Lowered `libdxilconv.dylib` deployment target to iOS 16.0.
- Removed the unavailable `quick_exit` dependency.

Result: progressed to the next dyld error.

## T2/T3 — GameController

The next missing class was `GCEventInteraction`, an iOS 18 GameController API.

The final working direction disabled the newer controller-interaction helper path and removed the hard loader dependency while preserving an older GameController binding.

Result: progressed to Metal.

## T4 — Metal residency sets

The next blocker was `MTLResidencySetDescriptor`.

XeniOS already contains a fallback path that does not require residency sets, so the patch forces `metal_residency_sets=false` and neutralizes the hard loader dependency.

Result: progressed to libc++ ABI dependencies.

## T5/T6 — libc++ exception/runtime helpers

Back-deployment exposed newer libc++ runtime dependencies not shipped by iOS 16, including exception-pointer helpers and `__libcpp_verbose_abort`.

The patch redirects/neutralizes only the required compatibility paths so dyld can continue loading.

Result: progressed to floating-point formatting imports.

## T7/T8 — floating `std::to_chars`

The binary imported newer floating-point `std::to_chars` overloads unavailable in the iOS 16 libc++ runtime.

All related overloads were handled together with a minimal local compatibility path. T8 corrected a malformed placeholder Mach-O symbol encoding introduced during T7.

Result: all missing-symbol crashes were cleared.

## T9 — Objective-C `__DATA_CONST`

T8 reached Objective-C runtime image loading, then crashed with `SIGBUS` in `libobjc` while processing the `MTLCommandQueue` protocol reference. The attempted runtime write landed in XeniOS's read-only `__DATA_CONST` mapping.

T9 removes the read-only segment behavior so iOS 16's Objective-C runtime can complete protocol metadata canonicalization/fixups.

**Result: XeniOS launches successfully into the Library UI.**

T9 is the current **golden launch baseline**. Further work should branch from T9 and avoid changing launch compatibility unless a later test proves it necessary.

## T10 — experimental clock mutex bypass

The first Forza Motorsport 4 launch attempt from T9 entered the emulator thread but aborted after `std::__1::mutex::lock()` threw a `std::system_error` from `xe::QueryGuestSystemTimeOffset()`.

T10 changes the branch at file offset `0x169474` in the T9 executable:

```text
E1 02 00 54    ; b.ne ...
->
1F 20 03 D5    ; nop
```

This forces the function to remain on Xenia's existing `clock_no_scaling`-style host-time path rather than entering the mutex-backed guest clock update path.

Reference experimental T10 executable SHA-256:

```text
68eb7008f2c036177c81b60decfe01f7ca33059012cf49404a2a7c8ffe827f7a
```

Reference tested T10 IPA SHA-256:

```text
16b4a118a7e9d3839c77cb0bcec7d77e8c3b43281f915f38612182fc4bd90bf1
```

Latest result: the earlier mutex analytics crash was no longer produced, but Forza Motorsport 4 still did not boot. `xenia.log` showed repeated `BaseHeap::AllocFixed attempting commit on unreserved page` warnings. More testing with a second, simpler title is required before changing guest memory behavior.
