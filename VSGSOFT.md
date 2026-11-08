# VSGSoft RustDeskMCP

A separate RustDeskMCP client with the VSGSoft RustDesk OSS server preset.
Downloads: https://pbardov.github.io/RustdeskMCP/
Ordinary client: https://pbardov.github.io/rustdesk/

## Platforms and use

- Windows x64: portable EXE or extract the ZIP and run `RustDeskMCP.exe`.
- Linux x64: extract the tar.gz and run `./RustDeskMCP/RustDeskMCP`. System GTK 3, X11, libxdo, PulseAudio, VA-API, PAM, GStreamer, EGL/OpenGL and appindicator libraries are required, as for upstream RustDesk. No system service is installed by the archive.
- macOS Intel and Apple Silicon: copy `RustDeskMCP.app` from the DMG into Applications. Grant Screen Recording and Accessibility permissions as needed.

The native application name and configuration profile are `RustDeskMCP`; Linux application ID and macOS bundle ID are `com.vsgsoft.RustDeskMCP`. This keeps it separate from ordinary RustDesk. Published distributions are unsigned; Windows SmartScreen or macOS Gatekeeper may request approval.

## Server preset

`vsgsoft/server.json` contains the public profile: ID server `rustdesk.vsgsoft.com`, relay `rustdesk.vsgsoft.com:21117`, and its public Ed25519 key. No API service or unattended access password is embedded. Existing user server settings take precedence. Upstream update checks are disabled by default, so updates are downloaded from this fork's page.

## MCP

Open Settings -> Security -> Enable MCP server. Point an MCP client that supports Streamable HTTP at `http://127.0.0.1:59940/mcp`. Keep the GUI running on the same computer. MCP is disabled by default and listens only on loopback. It does not need a new VPS service, public port, or Caddy route.

Upstream reference: https://github.com/YaoxinCS/RustdeskMCP/blob/main/docs/RustDeskMCP.md

## Automation

The `VSGSoft MCP client` Actions workflow runs daily and on customization changes, and can be dispatched manually. It follows the latest stable **YaoxinCS/RustdeskMCP** release, preserving the MCP implementation, rather than replacing it with official RustDesk sources. The current upstream is `v1.4.6-mcp.1`.

The prepare job replaces application files with the exact release tree, reapplies `vsgsoft/configure.py`, records `vsgsoft/upstream.json`, and pushes a normal commit on `vsgsoft`. The custom workflow and scripts are preserved. Patches fail if expected upstream anchors disappear. Releases are identified by upstream tag plus customization hash. Already published combinations are skipped; `force_rebuild` creates a new release tag.

Build jobs use the upstream dependency versions and pinned action commits. They verify the native binaries contain the complete public server profile and MCP implementation. Linux additionally launches the actual GUI in Xvfb with temporary profiles and verifies disabled HTTP 503, initialization, the 13 MCP tool schemas, and ping. No remote-control action is executed by this check.

Publication requires every platform job to succeed. GitHub Releases contain packages, SHA256SUMS, a manifest and a complete source archive including submodules, under the upstream AGPL-3.0 license and notices. GitHub Pages links to these immutable release assets.

Runtime customization loads public defaults in `src/vsgsoft_config.rs`, calls it from `src/common.rs`/`src/lib.rs`, and makes the upstream `pre_global_init_app_name` default to RustDeskMCP. The Windows portable packer uses its own `rustdeskmcp` extraction folder and `RuntimeBroker_rustdeskmcp.exe` helper name, also matched in `src/privacy_mode/win_topmost_window.rs`. Packaging identity changes are in Linux CMake, macOS AppInfo/project/URL scheme, and macOS paths in `build.py`. The MCP protocol and remote-session implementation are retained from upstream.
