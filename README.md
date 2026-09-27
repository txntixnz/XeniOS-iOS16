# XeniOS iOS 16 Backport

Experimental compatibility patch for launching **XeniOS 2.0.1 build 9849** on **iOS 16.0**.

## Status

**Field-validated launch baseline: T9**

Validated on:

- iPhone 13 Pro Max (`iPhone14,3`)
- iOS 16.0 (`20A362`)
- TrollStore + Dopamine
- XeniOS 2.0.1 build 9849

The T9 build reaches the XeniOS Library UI and reports **JIT Enabled**.

**Current game-boot experiment: T10**

T10 branches from T9 and forces `QueryGuestSystemTimeOffset()` down Xenia's no-scaling clock path to bypass an iOS 16 `std::mutex::lock()` / `std::system_error` failure observed when starting Forza Motorsport 4. T10 no longer produced that analytics crash in the latest test, but the game still did not boot. The latest `xenia.log` instead showed two `BaseHeap::AllocFixed attempting commit on unreserved page` warnings plus orientation warnings. T10 is therefore **experimental and not a replacement for T9**.

## What this repo contains

This repository does **not** redistribute XeniOS or games. Instead, `patch_ios16.py` applies the exact field-validated T9 compatibility edits to the specific upstream IPA used during testing.

The patcher validates the input IPA by SHA-256 before changing anything, then verifies the patched Mach-O executable and `libdxilconv.dylib` hashes after modification.

## Usage

Requires Python 3.

```bash
python patch_ios16.py xenios_ios_iphone_ipad.ipa
```

Optional output name:

```bash
python patch_ios16.py xenios_ios_iphone_ipad.ipa XeniOS_iOS16_T9.ipa
```

Install the resulting IPA with TrollStore. The original code signature is intentionally removed because the modified app must be re-signed at installation.

## Validated input

```text
XeniOS version: 2.0.1
Build:          9849
Input IPA SHA:  ec277f6effa363d2b311ce5bdb0510b0e4630ea0b31aed08ad8a31eb42656336
```

If your IPA has a different SHA-256, the script intentionally refuses to patch it. Do not remove that safety check and assume offsets are compatible with another XeniOS build.

## What T9 fixes

The original iOS 18-targeted binary failed on iOS 16 before reaching the UI. The validated patch chain addressed:

1. iOS 18 Mach-O deployment target / plist deployment target.
2. unavailable `quick_exit` runtime dependency.
3. iOS 18 `GCEventInteraction` hard dependency.
4. Metal residency-set dependencies unavailable on iOS 16.
5. newer libc++ exception-runtime dependencies.
6. newer floating-point `std::to_chars` dependencies.
7. Objective-C protocol fixups faulting inside read-only `__DATA_CONST` on iOS 16.

The decisive T9 change leaves the relevant `__DATA_CONST` segment writable rather than allowing dyld to lock it read-only before the iOS 16 Objective-C runtime finishes its protocol metadata fixups.

See [`docs/PATCH_NOTES.md`](docs/PATCH_NOTES.md) for the test-by-test history.

## Important limitations

- This is an **experimental backport**, not an official XeniOS build.
- Launching the frontend is validated; Xbox 360 game execution on this iOS 16 configuration is not yet validated.
- Some compatibility shims are deliberately minimal and may need replacement with source-level backports as testing moves deeper into emulator/game initialization.
- JIT is still required for translated game code.

## Upstream / attribution

XeniOS is an iOS/macOS port in the Xenia project lineage and is maintained separately by the XeniOS project. This repository is an independent compatibility experiment and is not affiliated with or endorsed by XeniOS, Xenia, Microsoft, or Apple.

The upstream Xenia/XeniOS license notice is preserved in [`third_party/XENIA_LICENSE.txt`](third_party/XENIA_LICENSE.txt).

No games, firmware, copyrighted game assets, or upstream IPA are included.
