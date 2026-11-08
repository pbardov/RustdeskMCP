#!/usr/bin/env python3
"""Publish a complete release and generate its GitHub Pages download page."""

import hashlib
import html
import json
import os
from pathlib import Path
import subprocess
import tarfile
from urllib.parse import quote


def gh(*args, **kwargs):
    return subprocess.run(["gh", *args], check=True, text=True, **kwargs)


def main():
    dist = Path("dist")
    version, tag, repo, source = (os.environ[k] for k in ["VERSION", "RELEASE_TAG", "GITHUB_REPOSITORY", "SOURCE_SHA"])
    required = ["windows-x86_64.exe", "windows-x86_64.zip", "linux-x86_64.tar.gz", "macos-x86_64.dmg", "macos-aarch64.dmg"]
    names = [p.name for p in dist.iterdir() if p.is_file()]
    for suffix in required:
        if not any(name.endswith(suffix) for name in names):
            raise RuntimeError(f"Incomplete release: missing {suffix}")
    source_name = f"rustdeskmcp-vsgsoft-{version}-source.tar.gz"
    tracked = subprocess.check_output(["git", "ls-files", "--recurse-submodules", "-z"]).decode().split("\0")
    with tarfile.open(dist / source_name, "w:gz") as archive:
        for filename in tracked:
            if filename and Path(filename).is_file():
                archive.add(filename, arcname=f"rustdeskmcp-vsgsoft-{version}/{filename}", recursive=False)
    artifacts = []
    for path in sorted(dist.iterdir()):
        if path.is_file():
            artifacts.append({"name": path.name, "size": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {
        "version": version, "release": tag, "source_commit": source,
        "upstream": json.loads(Path("vsgsoft/upstream.json").read_text()),
        "server": json.loads(Path("vsgsoft/server.json").read_text()),
        "mcp": {"url": "http://127.0.0.1:59940/mcp", "enabled_by_default": False, "application": "RustDeskMCP"},
        "artifacts": artifacts,
    }
    (dist / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    sums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(dist.iterdir()) if p.is_file())
    (dist / "SHA256SUMS").write_text(sums)
    notes = Path("release-notes.txt")
    notes.write_text(
        f"RustDeskMCP {version}, built with VSGSoft server defaults.\n\n"
        "ID server: rustdesk.vsgsoft.com\nRelay: rustdesk.vsgsoft.com:21117\n\n"
        f"Custom source: https://github.com/{repo}/tree/{source}\n"
        f"Upstream source: {manifest['upstream']['commit']}\n\n"
        "Windows x64: portable EXE and ZIP. Linux x64: portable tar.gz. macOS: Intel and Apple Silicon DMG.\n\n"
        "The distributions are unsigned. Windows SmartScreen / macOS Gatekeeper may require approval.\n"
        "MCP is disabled by default. Enable it in Settings -> Security -> Enable MCP server.\n"
        "Local Streamable HTTP endpoint: http://127.0.0.1:59940/mcp\n"
        "The application uses a separate RustDeskMCP profile.\n"
        "Server settings are defaults; existing user configuration takes precedence.\n"
        "Use the VSGSoft download page for updates. Upstream update checks are disabled by default.\n\n"
        "SHA256SUMS, manifest.json and the complete source archive (including submodules) are included.\n"
    )
    existing = subprocess.run(["gh", "release", "view", tag, "--repo", repo, "--json", "isDraft"], capture_output=True, text=True)
    if existing.returncode:
        gh("release", "create", tag, "--repo", repo, "--target", source, "--draft", "--title", f"VSGSoft RustDeskMCP {version}", "--notes-file", str(notes))
    elif not json.loads(existing.stdout)["isDraft"]:
        raise RuntimeError("A published release already exists; use Force rebuild for a new release")
    gh("release", "upload", tag, "--repo", repo, "--clobber", *[str(p) for p in sorted(dist.iterdir()) if p.is_file()])
    gh("release", "edit", tag, "--repo", repo, "--draft=false", "--latest")
    site = Path("site")
    site.mkdir(exist_ok=True)
    release_url = f"https://github.com/{repo}/releases/tag/{quote(tag)}"
    download_url = f"https://github.com/{repo}/releases/download/{quote(tag)}/"
    rows = []
    labels = {
        "windows-x86_64.exe": "Windows · Portable EXE",
        "windows-x86_64.zip": "Windows · Portable ZIP",
        "linux-x86_64.tar.gz": "Linux x64 · Portable tar.gz",
        "macos-x86_64.dmg": "macOS · Intel",
        "macos-aarch64.dmg": "macOS · Apple Silicon",
        "source.tar.gz": "Исходный код",
    }
    for item in artifacts:
        label = next((label for suffix, label in labels.items() if item["name"].endswith(suffix)), item["name"])
        rows.append(f'<a class="download" href="{download_url}{quote(item["name"])}"><strong>{html.escape(label)}</strong><span>{item["size"] / 1024 / 1024:.1f} MB ↗</span></a>')
    template = """<!doctype html>
<html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VSGSoft · RustDeskMCP</title>
<style>body{font:17px/1.6 system-ui,sans-serif;background:#101923;color:#e9f0f7;margin:0}main{max-width:850px;margin:70px auto;padding:0 24px}a{color:#80dbd2}h1{font-size:42px;line-height:1.15}small,.muted{color:#a9b7c7}.downloads{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin:30px 0}.download{background:#1d2c3c;padding:18px;border-radius:12px;text-decoration:none;display:flex;justify-content:space-between;gap:12px}.download:hover{background:#2a4055}.download span{color:#a9b7c7;font-size:13px}code{overflow-wrap:anywhere}footer{border-top:1px solid #2a4055;margin-top:38px;padding-top:20px;font-size:14px}</style>
<main><small>VSGSOFT · УДАЛЁННАЯ ПОДДЕРЖКА</small><h1>RustDeskMCP<br>для сервера VSGSoft</h1>
<p class="muted">Версия VERSION. Скачайте приложение для своей системы. Сервер VSGSoft и его публичный ключ уже заданы.</p>
<div class="downloads">DOWNLOADS</div>
<p>В Windows запустите EXE либо распакуйте ZIP и запустите RustDeskMCP.exe. В Linux распакуйте tar.gz и запустите ./RustDeskMCP/RustDeskMCP; требуются системные библиотеки GTK 3, X11, libxdo, PulseAudio, VA-API, PAM и GStreamer. В macOS перенесите приложение из DMG в «Программы» и разрешите доступ к записи экрана и универсальному доступу.</p>
<p>Чтобы подключить AI-клиент, откройте <strong>Настройки → Безопасность → Enable MCP server</strong>. Адрес Streamable HTTP: <code>http://127.0.0.1:59940/mcp</code>. Приложение должно быть запущено на том же компьютере. MCP выключен по умолчанию.</p>
<p>RustDeskMCP использует отдельный профиль и может запускаться рядом с <a href="https://pbardov.github.io/rustdesk/">обычным клиентом VSGSoft</a>. <a href="https://github.com/YaoxinCS/RustdeskMCP/blob/main/docs/RustDeskMCP.md">Документация MCP</a>.</p>
<p class="muted">Сборки не подписаны сертификатами Microsoft / Apple. Система может запросить подтверждение запуска. Обновления доступны на этой странице.</p>
<footer><a href="RELEASE_URL">Релиз</a> · <a href="SUMS_URL">SHA256</a> · <a href="MANIFEST_URL">Состав сборки</a> · <a href="SOURCE_URL">Исходники · AGPL-3.0</a><p class="muted">На уже настроенном RustDeskMCP сохраняются пользовательские параметры сервера.</p></footer></main></html>
"""
    replacements = {
        "VERSION": html.escape(version), "DOWNLOADS": "\n".join(rows),
        "RELEASE_URL": release_url, "SUMS_URL": download_url + "SHA256SUMS",
        "MANIFEST_URL": download_url + "manifest.json",
        "SOURCE_URL": f"https://github.com/{repo}/tree/{source}",
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    (site / "index.html").write_text(template)
    (site / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (site / ".nojekyll").touch()
    print("Published:", release_url)


if __name__ == "__main__":
    main()
