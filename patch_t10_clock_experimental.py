#!/usr/bin/env python3
"""Apply the experimental T10 clock bypass to the validated T9 IPA.

This is NOT the golden patch. T9 remains the field-validated launch baseline.
"""
from __future__ import annotations
import argparse, hashlib, shutil, tempfile, zipfile
from pathlib import Path

T9_IPA_SHA256 = "5a16c29e4caa3808546dca83be665bd2a5eda8d0f760f7b3967689e359f7b5ff"
T9_EXE_SHA256 = "d14f6b5a65e19f5fd6cd0472708076c24f737bbaa28dc8db6dbb22169436fe4c"
T10_EXE_SHA256 = "68eb7008f2c036177c81b60decfe01f7ca33059012cf49404a2a7c8ffe827f7a"
OFFSET = 0x169474
OLD = bytes.fromhex("e1020054")
NEW = bytes.fromhex("1f2003d5")

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input_t9_ipa", type=Path)
    ap.add_argument("output_ipa", nargs="?", type=Path, default=Path("XeniOS_2.0.1_iOS16_LAUNCH_TEST10.ipa"))
    a=ap.parse_args()
    if sha256(a.input_t9_ipa) != T9_IPA_SHA256:
        raise SystemExit("Refusing to patch: input IPA is not the validated reference T9 IPA.")
    with tempfile.TemporaryDirectory(prefix="xenios-t10-") as td:
        root=Path(td)
        with zipfile.ZipFile(a.input_t9_ipa) as z: z.extractall(root)
        app=next((root/"Payload").glob("*.app"))
        exe=app/"XeniOS"
        if sha256(exe) != T9_EXE_SHA256:
            raise SystemExit("Unexpected T9 executable hash.")
        data=bytearray(exe.read_bytes())
        if data[OFFSET:OFFSET+4] != OLD:
            raise SystemExit(f"Unexpected bytes at 0x{OFFSET:X}.")
        data[OFFSET:OFFSET+4]=NEW
        exe.write_bytes(data)
        if sha256(exe) != T10_EXE_SHA256:
            raise SystemExit("T10 executable verification failed.")
        shutil.rmtree(app/"_CodeSignature", ignore_errors=True)
        a.output_ipa.parent.mkdir(parents=True, exist_ok=True)
        if a.output_ipa.exists(): a.output_ipa.unlink()
        with zipfile.ZipFile(a.output_ipa,"w",compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(root.rglob("*")):
                if p.is_file(): z.write(p,p.relative_to(root))
    print("Wrote", a.output_ipa)
    print("Executable SHA-256 verified:", T10_EXE_SHA256)

if __name__ == "__main__": main()
