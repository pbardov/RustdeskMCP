#!/usr/bin/env python3
"""Verify that a built native library contains the requested public server profile."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    profile = json.loads(Path("vsgsoft/server.json").read_text())
    needles = [profile[k].encode() for k in ["id_server", "relay_server", "public_key"]]
    # LLVM can emit the short application name as inline machine-code stores.
    # Its runtime identity is checked by the GUI/profile smoke test instead.
    needles += [b"127.0.0.1:59940", b"enable-mcp-server", b"open_desktop_session", b"terminal_input"]
    candidates = 0
    for root in args.paths:
        files = root.rglob("*") if root.is_dir() else [root]
        for path in files:
            if not path.is_file() or path.suffix.lower() not in [".dll", ".so", ".dylib", ".exe", ""]:
                continue
            if path.stat().st_size < 100_000:
                continue
            content = path.read_bytes()
            candidates += 1
            if all(value in content for value in needles):
                print("Verified embedded server profile and MCP implementation:", path)
                return
            if "rustdesk" in path.name.lower():
                missing = [value.decode() for value in needles if value not in content]
                print("Missing expected public strings in", path, ":", missing)
    if not candidates:
        print("No native library or executable was found in:", args.paths)
    raise SystemExit("No native binary contains the complete VSGSoft server profile and MCP implementation")


if __name__ == "__main__":
    main()
