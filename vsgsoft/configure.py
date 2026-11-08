#!/usr/bin/env python3
"""Embed the public server profile using RustDesk's existing default settings."""

import argparse
import base64
import json
from pathlib import Path


def configure(root: Path) -> None:
    profile = json.loads((root / "vsgsoft/server.json").read_text())
    if len(base64.b64decode(profile["public_key"], validate=True)) != 32:
        raise ValueError("The server public key must be an Ed25519 public key")
    if not profile["id_server"] or "://" in profile["id_server"]:
        raise ValueError("The ID server must be a hostname, without a URL scheme")
    settings = {
        "custom-rendezvous-server": profile["id_server"],
        "relay-server": profile["relay_server"],
        "key": profile["public_key"],
        "api-server": profile["api_server"],
    }
    pairs = "\n".join(
        f"        ({json.dumps(k)}, {json.dumps(v)})," for k, v in settings.items()
    )
    module = """use hbb_common::config::{DEFAULT_LOCAL_SETTINGS, DEFAULT_SETTINGS};

pub fn apply() {
    crate::common::pre_global_init_app_name();
    let mut defaults = DEFAULT_SETTINGS.write().unwrap();
    for (key, value) in [
PAIRS
    ] {
        defaults
            .entry(key.to_owned())
            .or_insert_with(|| value.to_owned());
    }
    drop(defaults);
    DEFAULT_LOCAL_SETTINGS
        .write()
        .unwrap()
        .entry("enable-check-update".to_owned())
        .or_insert_with(|| "N".to_owned());
}
""".replace("PAIRS", pairs)
    (root / "src/vsgsoft_config.rs").write_text(module)
    patches = [
        ("src/lib.rs", "mod custom_server;\n", "mod vsgsoft_config;\n"),
        (
            "src/common.rs",
            "pub fn load_custom_client() {\n",
            "    crate::vsgsoft_config::apply();\n",
        ),
    ]
    for name, anchor, insertion in patches:
        path = root / name
        text = path.read_text()
        if text.count(anchor) != 1:
            raise RuntimeError(f"Upstream entry point changed: {name}")
        if insertion not in text:
            path.write_text(text.replace(anchor, anchor + insertion))
    replacements = {
        "src/common.rs": [(
            "    let Some(app_name) = app_name else {\n        return;\n    };",
            '    let app_name = app_name.unwrap_or_else(|| "RustDeskMCP".to_owned());',
        )],
        "flutter/linux/CMakeLists.txt": [(
            'set(APPLICATION_ID "com.carriez.flutter_hbb")',
            'set(APPLICATION_ID "com.vsgsoft.RustDeskMCP")',
        )],
        "flutter/macos/Runner/Configs/AppInfo.xcconfig": [
            ("PRODUCT_NAME = RustDesk\n", "PRODUCT_NAME = RustDeskMCP\n"),
            ("PRODUCT_BUNDLE_IDENTIFIER = com.carriez.flutterHbb", "PRODUCT_BUNDLE_IDENTIFIER = com.vsgsoft.RustDeskMCP"),
        ],
        "flutter/macos/Runner.xcodeproj/project.pbxproj": [("RustDesk.app", "RustDeskMCP.app")],
        "build.py": [("RustDesk.app", "RustDeskMCP.app")],
    }
    if not (root / "src/agent_bridge.rs").is_file():
        raise RuntimeError("Upstream source does not contain the MCP implementation")
    for name, changes in replacements.items():
        path = root / name
        text = path.read_text()
        for before, after in changes:
            if after in text and before not in text:
                continue
            if before not in text:
                raise RuntimeError(f"Upstream application identity changed: {name}")
            text = text.replace(before, after)
        path.write_text(text)
    print("Embedded server profile:", profile["id_server"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    configure(parser.parse_args().root.resolve())
