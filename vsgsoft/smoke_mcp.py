#!/usr/bin/env python3
"""Exercise the actual Linux GUI's MCP endpoint in an isolated profile."""

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

URL = "http://127.0.0.1:59940/mcp"
TOOLS = {
    "open_desktop_session", "open_terminal_session", "terminal_input", "terminal_output",
    "lock_remote_user_input", "unlock_remote_user_input", "input_password",
    "select_desktop_display", "get_desktop_frame", "mouse_move", "mouse_click",
    "keyboard_input", "keyboard_hotkey",
}


def request(method, params=None, notification=False):
    body = {"jsonrpc": "2.0", "method": method}
    if not notification:
        body["id"] = 1
    if params is not None:
        body["params"] = params
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        data = response.read()
        return response.status, json.loads(data) if data else None


def exercise(binary, enabled, folder):
    config_root = folder / ("enabled" if enabled else "disabled")
    config_root.mkdir()
    if enabled:
        config = config_root / "rustdeskmcp/RustDeskMCP_local.toml"
        config.parent.mkdir()
        config.write_text('[options]\nenable-mcp-server = "Y"\n')
    env = os.environ.copy()
    env.update({
        "XDG_CONFIG_HOME": str(config_root), "XDG_CACHE_HOME": str(config_root / "cache"),
        "LD_LIBRARY_PATH": str(binary.parent / "lib"), "LIBGL_ALWAYS_SOFTWARE": "1",
        "RUSTDESK_MCP_APP_NAME": "RustDeskMCP",
    })
    with (folder / ("enabled.log" if enabled else "disabled.log")).open("w") as log:
        proc = subprocess.Popen(
            ["dbus-run-session", "--", "xvfb-run", "-a", str(binary)],
            env=env, stdout=log, stderr=log, start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 90
            while True:
                if proc.poll() is not None:
                    raise RuntimeError(f"GUI exited before MCP was ready: {proc.returncode}")
                try:
                    status, data = request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "vsgsoft-ci", "version": "1"}})
                    break
                except (OSError, TimeoutError):
                    if time.monotonic() > deadline:
                        raise RuntimeError("MCP endpoint did not start within 90 seconds")
                    time.sleep(1)
            if not enabled:
                assert status == 503 and data["error"]["code"] == -32000, (status, data)
                print("PASS: fresh profile refuses MCP requests with HTTP 503")
                return
            assert status == 200, (status, data)
            assert data["result"]["protocolVersion"] == "2025-11-25", data
            assert data["result"]["capabilities"]["tools"] == {"listChanged": False}, data
            assert request("notifications/initialized", notification=True) == (202, None)
            status, data = request("tools/list")
            assert status == 200 and TOOLS <= {tool["name"] for tool in data["result"]["tools"]}, data
            assert request("ping")[1]["result"] == {}
            print("PASS: initialize, initialized, tools/list (13 tools) and ping")
        finally:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            for _ in range(30):
                with socket.socket() as client:
                    if client.connect_ex(("127.0.0.1", 59940)) != 0:
                        break
                time.sleep(0.2)
            else:
                raise RuntimeError("MCP process did not stop")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    args = parser.parse_args()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 59940))
    with tempfile.TemporaryDirectory(prefix="vsgsoft-mcp-smoke-") as folder:
        exercise(args.binary.resolve(), False, Path(folder))
        exercise(args.binary.resolve(), True, Path(folder))


if __name__ == "__main__":
    main()
