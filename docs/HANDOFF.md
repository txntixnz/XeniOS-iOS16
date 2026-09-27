# Handoff / golden baseline

## Current source of truth

**XeniOS iOS16 Launch Test 9 (T9)** is the first field-validated build that launches to the XeniOS Library UI on the test device.

### Device

- iPhone 13 Pro Max / iPhone14,3
- iOS 16.0 / 20A362
- TrollStore
- Dopamine jailbreak

### Upstream binary

- XeniOS 2.0.1
- build 9849
- source IPA SHA-256: `ec277f6effa363d2b311ce5bdb0510b0e4630ea0b31aed08ad8a31eb42656336`

### Reference T9 artifact

- reference IPA SHA-256: `5a16c29e4caa3808546dca83be665bd2a5eda8d0f760f7b3967689e359f7b5ff`
- patched main executable SHA-256: `d14f6b5a65e19f5fd6cd0472708076c24f737bbaa28dc8db6dbb22169436fe4c`
- patched `libdxilconv.dylib` SHA-256: `3eff622e17a47fa90ad06e5f63170927621dce13676f65ae9fa9bd02fa3cb362`

## Freeze rule

Treat T9 as a launch-compatible golden baseline. For game-boot testing, make the smallest possible change from T9 and keep a copy of T9 unchanged.

## Next validation

1. Import one legally owned Xbox 360 title.
2. Verify it appears in the Library.
3. Attempt launch with JIT enabled.
4. Capture XeniOS log/crash analytics if game initialization fails.
5. Distinguish frontend/iOS compatibility failures from emulator/game compatibility failures before modifying the launch backport.

## Current experimental branch: T10

T10 is derived from T9 and changes one ARM64 branch in `xe::QueryGuestSystemTimeOffset()` so the function always takes the existing no-scaling host-time path.

Reason: the first Forza Motorsport 4 launch test on T9 reached the emulator thread and aborted in `std::__1::mutex::lock()` from `xe::QueryGuestSystemTimeOffset()`.

Observed T10 status:

- XeniOS frontend still launches.
- JIT still reports enabled.
- Forza Motorsport 4 is detected and listed as playable.
- Selecting Play does not successfully boot the game.
- The latest T10 attempt produced no iOS analytics crash.
- `xenia.log` contained two `BaseHeap::AllocFixed attempting commit on unreserved page` warnings and two iOS orientation warnings.

**Do not promote T10 to golden.** Keep T9 frozen until a game successfully boots or a later change is proven broadly safer.
