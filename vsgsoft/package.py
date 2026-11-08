#!/usr/bin/env python3
"""Collect platform packages under unambiguous VSGSoft distribution names."""

import argparse
import os
from pathlib import Path
import shutil
import tarfile
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("platform", choices=["windows", "linux", "macos"])
    parser.add_argument("arch")
    args = parser.parse_args()
    version = os.environ["VERSION"]
    base = f"rustdeskmcp-vsgsoft-{version}-{args.platform}-{args.arch}"
    dist = Path("dist")
    dist.mkdir(exist_ok=True)
    if args.platform == "windows":
        sources = [(Path(f"SignOutput/rustdesk-{version}-{args.arch}.exe"), f"{base}.exe")]
        if not Path("rustdesk/RustDeskMCP.exe").is_file():
            raise RuntimeError("Missing named MCP executable")
        with zipfile.ZipFile(dist / f"{base}.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(Path("rustdesk").rglob("*")):
                if path.is_file():
                    archive.write(path, Path("RustDeskMCP") / path.relative_to("rustdesk"))
    elif args.platform == "macos":
        sources = [(Path(f"rustdesk-{version}-{args.arch}.dmg"), f"{base}.dmg")]
    else:
        sources = []
        bundle = Path("flutter/build/linux/x64/release/bundle")
        if not (bundle / "rustdesk").is_file() or not (bundle / "lib/librustdesk.so").is_file():
            raise RuntimeError("Missing Linux executable or Rust library")
        with tarfile.open(dist / f"{base}.tar.gz", "w:gz") as archive:
            for path in sorted(bundle.rglob("*")):
                relative = path.relative_to(bundle)
                if str(relative) == "rustdesk":
                    relative = Path("RustDeskMCP")
                archive.add(path, arcname=Path("RustDeskMCP") / relative, recursive=False)
    for source, name in sources:
        if not source.is_file() or source.stat().st_size < 100_000:
            raise RuntimeError(f"Missing or empty build output: {source}")
        shutil.copy2(source, dist / name)
        print("Package:", dist / name)


if __name__ == "__main__":
    main()
