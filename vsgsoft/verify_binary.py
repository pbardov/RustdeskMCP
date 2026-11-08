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
    needles += [b"127.0.0.1:59940", b"enable-mcp-server", b"open_desktop_session", b"terminal_input", b"RustDeskMCP"]
    for root in args.paths:
        files = root.rglob("*") if root.is_dir() else [root]
        for path in files:
            if not path.is_file() or path.suffix.lower() not in [".dll", ".so", ".dylib", ".exe", ""]:
                continue
            if path.stat().st_size < 100_000:
                continue
            content = path.read_bytes()
            if all(value in content for value in needles):
                print("Verified embedded server profile and MCP implementation:", path)
                return
    raise SystemExit("No native binary contains the complete VSGSoft server profile and MCP implementation")


if __name__ == "__main__":
    main()
