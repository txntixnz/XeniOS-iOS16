#!/usr/bin/env python3
"""Reproduce the field-validated XeniOS iOS 16 Launch Test 9 patch.

Target upstream IPA SHA-256:
  ec277f6effa363d2b311ce5bdb0510b0e4630ea0b31aed08ad8a31eb42656336

This script performs exact verified binary edits for that IPA only.
It does not contain or redistribute XeniOS itself.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import plistlib
import shutil
import tempfile
import zipfile
from pathlib import Path

SOURCE_IPA_SHA256 = "ec277f6effa363d2b311ce5bdb0510b0e4630ea0b31aed08ad8a31eb42656336"
SOURCE_EXE_SHA256 = "7d000b31b96eee0174504f5c6292e9fa7dd55f423bdce4676a213fe04a67db4d"
PATCHED_EXE_SHA256 = "d14f6b5a65e19f5fd6cd0472708076c24f737bbaa28dc8db6dbb22169436fe4c"
SOURCE_DXIL_SHA256 = "22dab0f75f713a71129bf089522ebccfaef0da307368328f39556870ccc406d9"
PATCHED_DXIL_SHA256 = "3eff622e17a47fa90ad06e5f63170927621dce13676f65ae9fa9bd02fa3cb362"
REFERENCE_T9_IPA_SHA256 = "5a16c29e4caa3808546dca83be665bd2a5eda8d0f760f7b3967689e359f7b5ff"

EXE_PATCHES = [
    (0x554, '10', '00'),
    (0xE36, '12', '10'),
    (0xC3FF48, 'fc6fbaa9fa67', 'c0035fd61f00'),
    (0xC3FF4F, 'a9f85f02a9f65703a9f44f04a9fd7b05a9ff8306d1f3', 'eb82000054020680520200003900040091e1031faac0'),
    (0xC3FF66, '00aa', '5fd6'),
    (0xC40130, 'ff8304d1', 'c0035fd6'),
    (0xEEFEB4, '10ab00f0106e41f900021fd610ab00f0107241f900021fd610ab00f0107641f900021fd610ab00f0107a41f900021fd610ab00f0107e41f900021fd610ab00f0108241f900021fd610ab00f0108641f900021fd610ab00f0108a41f900021fd610ab00f0108e41f900021fd6', '2640f5171f2003d51f2003d52340f5171f2003d51f2003d52040f5171f2003d51f2003d51d40f5171f2003d51f2003d51a40f5171f2003d51f2003d51740f5171f2003d51f2003d51440f5171f2003d51f2003d51140f5171f2003d51f2003d50e40f5171f2003d51f2003d5'),
    (0xEF00B8, '10ab00d0109642f900021fd6', 'c0035fd61f2003d51f2003d5'),
    (0x252C538, '6175746f00', '66616c7365'),
    (0x252C54F, '04', '05'),
    (0x25402F0, '1c', '01'),
    (0x25402F4, '536a', '4b02'),
    (0x2543772, '7175', '6578'),
    (0x2543775, '636b5f65786974', '74000000000000'),
    (0x2544A1A, '4576656e74496e74', '436f6e74726f6c6c'),
    (0x2544A24, '616374696f6e', '000000000000'),
    (0x2545040, '52', '54'),
    (0x2545042, '736964656e637953657444657363', '787475726544657363726970746f'),
    (0x2545051, '6970746f72', '0000000000'),
    (0x2547EC5, '4e53743133657863', '5374313763757272'),
    (0x2547ECE, '70', '6e'),
    (0x2547ED0, '696f6e5f70747233315f5f66726f6d5f6e61746976655f657863657074696f6e5f706f696e746572455076', '5f657863657074696f6e760000000000000000000000000000000000000000000000000000000000000000'),
    (0x2549F64, '4e5374335f5f3138746f5f636861727345506353305f64', '6e776d0000000000000000000000000000000000000000'),
    (0x2549F7F, '4e5374335f5f3138746f5f636861727345506353305f644e535f313263686172735f666f726d617445', '6e776d0000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x2549FAC, '4e5374335f5f3138746f5f636861727345506353305f644e535f313263686172735f666f726d61744569', '6e776d000000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x2549FDA, '4e5374335f5f3138746f5f636861727345506353305f65', '6e776d0000000000000000000000000000000000000000'),
    (0x2549FF5, '4e5374335f5f3138746f5f636861727345506353305f654e535f313263686172735f666f726d617445', '6e776d0000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x254A022, '4e5374335f5f3138746f5f636861727345506353305f654e535f313263686172735f666f726d61744569', '6e776d000000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x254A050, '4e5374335f5f3138746f5f636861727345506353305f66', '6e776d0000000000000000000000000000000000000000'),
    (0x254A06B, '4e5374335f5f3138746f5f636861727345506353305f664e535f313263686172735f666f726d617445', '6e776d0000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x254A098, '4e5374335f5f3138746f5f636861727345506353305f664e535f313263686172735f666f726d61744569', '6e776d000000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x254A995, '696e6974', '66726565'),
    (0x254A99A, '7072696d6172795f657863657074696f6e', '657863657074696f6e0000000000000000'),
    (0x280FEE0, 'e969', '2d84'),
    (0x280FEE7, '1c', '01'),
    (0x28675F8, '4576656e74496e74', '436f6e74726f6c6c'),
    (0x2867602, '616374696f6e', '000000000000'),
    (0x2867837, '52', '54'),
    (0x2867839, '736964656e637953657444657363', '787475726544657363726970746f'),
    (0x2867848, '6970746f72', '0000000000'),
    (0x286991F, '4e53743133657863', '5374313763757272'),
    (0x2869928, '70', '6e'),
    (0x286992A, '696f6e5f70747233315f5f66726f6d5f6e61746976655f657863657074696f6e5f706f696e746572455076', '5f657863657074696f6e760000000000000000000000000000000000000000000000000000000000000000'),
    (0x286BD2E, '4e5374335f5f3138746f5f636861727345506353305f64', '6e776d0000000000000000000000000000000000000000'),
    (0x286BD49, '4e5374335f5f3138746f5f636861727345506353305f644e535f313263686172735f666f726d617445', '6e776d0000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x286BD76, '4e5374335f5f3138746f5f636861727345506353305f644e535f313263686172735f666f726d61744569', '6e776d000000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x286BDA4, '4e5374335f5f3138746f5f636861727345506353305f65', '6e776d0000000000000000000000000000000000000000'),
    (0x286BDBF, '4e5374335f5f3138746f5f636861727345506353305f654e535f313263686172735f666f726d617445', '6e776d0000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x286BDEC, '4e5374335f5f3138746f5f636861727345506353305f654e535f313263686172735f666f726d61744569', '6e776d000000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x286BE1A, '4e5374335f5f3138746f5f636861727345506353305f66', '6e776d0000000000000000000000000000000000000000'),
    (0x286BE35, '4e5374335f5f3138746f5f636861727345506353305f664e535f313263686172735f666f726d617445', '6e776d0000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x286BE62, '4e5374335f5f3138746f5f636861727345506353305f664e535f313263686172735f666f726d61744569', '6e776d000000000000000000000000000000000000000000000000000000000000000000000000000000'),
    (0x286C9FA, '696e6974', '66726565'),
    (0x286C9FF, '7072696d6172795f657863657074696f6e', '657863657074696f6e0000000000000000'),
    (0x286E28C, '7175', '6578'),
    (0x286E28F, '636b5f65786974', '74000000000000'),
]

DXIL_PATCHES = [
    (0x6D6, '12', '10'),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def apply_patches(path: Path, patches, expected_before: str, expected_after: str) -> None:
    if sha256_file(path) != expected_before:
        raise SystemExit(f"Refusing to patch unexpected file: {path}")
    data = bytearray(path.read_bytes())
    for offset, old_hex, new_hex in patches:
        old = bytes.fromhex(old_hex)
        new = bytes.fromhex(new_hex)
        if len(old) != len(new):
            raise RuntimeError("Patch length mismatch")
        if data[offset:offset + len(old)] != old:
            raise RuntimeError(f"Unexpected bytes at 0x{offset:X} in {path.name}")
        data[offset:offset + len(old)] = new
    path.write_bytes(data)
    actual = sha256_file(path)
    if actual != expected_after:
        raise RuntimeError(f"Patched hash mismatch for {path}: {actual}")


def find_app(payload: Path) -> Path:
    apps = [p for p in payload.iterdir() if p.is_dir() and p.suffix == ".app"]
    if len(apps) != 1:
        raise RuntimeError(f"Expected one .app in Payload, found {len(apps)}")
    return apps[0]


def main() -> None:
    ap = argparse.ArgumentParser(description="Patch the validated XeniOS 2.0.1/9849 IPA for iOS 16.0 startup.")
    ap.add_argument("input_ipa", type=Path)
    ap.add_argument("output_ipa", nargs="?", type=Path, default=Path("XeniOS_2.0.1_iOS16_LAUNCH_TEST9.ipa"))
    args = ap.parse_args()

    if sha256_file(args.input_ipa) != SOURCE_IPA_SHA256:
        raise SystemExit(
            "Input IPA does not match the validated upstream build.\n"
            f"Expected SHA-256: {SOURCE_IPA_SHA256}\n"
            f"Actual SHA-256:   {sha256_file(args.input_ipa)}"
        )

    with tempfile.TemporaryDirectory(prefix="xenios-ios16-") as td:
        root = Path(td)
        with zipfile.ZipFile(args.input_ipa, "r") as zf:
            zf.extractall(root)

        app = find_app(root / "Payload")
        exe = app / "XeniOS"
        dxil = app / "Frameworks" / "libdxilconv.dylib"

        apply_patches(exe, EXE_PATCHES, SOURCE_EXE_SHA256, PATCHED_EXE_SHA256)
        apply_patches(dxil, DXIL_PATCHES, SOURCE_DXIL_SHA256, PATCHED_DXIL_SHA256)

        info = app / "Info.plist"
        with info.open("rb") as f:
            plist = plistlib.load(f)
        plist["MinimumOSVersion"] = "16.0"
        plist["CFBundleDisplayName"] = "XeniOS iOS16 T9"
        with info.open("wb") as f:
            plistlib.dump(plist, f, fmt=plistlib.FMT_XML, sort_keys=False)

        # Original signature is invalid after modification; TrollStore will re-sign.
        shutil.rmtree(app / "_CodeSignature", ignore_errors=True)

        args.output_ipa.parent.mkdir(parents=True, exist_ok=True)
        if args.output_ipa.exists():
            args.output_ipa.unlink()
        with zipfile.ZipFile(args.output_ipa, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(root))

    print(f"Wrote: {args.output_ipa}")
    print(f"Output SHA-256: {sha256_file(args.output_ipa)}")
    print("Note: ZIP metadata may make the whole-IPA checksum differ from the reference T9,")
    print("but the patched executable/dylib hashes are verified byte-for-byte.")


if __name__ == "__main__":
    main()
