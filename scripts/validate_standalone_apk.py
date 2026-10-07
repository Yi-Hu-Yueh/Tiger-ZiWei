"""Read-only off-device APK validation. Never emits secret values."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def dex_strings(data: bytes) -> list[str]:
    assert data.startswith(b"dex\n"), "invalid DEX"
    count, offset = struct.unpack_from("<II", data, 56)
    result = []
    for index in range(count):
        position = struct.unpack_from("<I", data, offset + 4 * index)[0]
        while data[position] & 0x80:
            position += 1
        position += 1
        end = data.index(b"\0", position)
        result.append(data[position:end].decode("utf-8", errors="replace"))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=Path)
    args = parser.parse_args()
    path = args.apk.resolve()
    assert path.is_file() and path.stat().st_size > 0
    all_strings = []
    with zipfile.ZipFile(path) as archive:
        entries = archive.namelist()
        for required in ("AndroidManifest.xml", "resources.arsc", "classes.dex", "assets/ziwei.html", "assets/ziwei.css", "assets/ziwei.js", "assets/THIRD_PARTY_NOTICES.txt", "assets/GSON-LICENSE.txt", "assets/LUNAR-JAVA-LICENSE.txt"):
            assert required in entries, f"missing required APK entry: {required}"
        for name in entries:
            assert not re.search(r"(?:^|/)\.env(?:$|\.)", name), "environment file packaged"
            assert not any(term in name.lower() for term in ("python.exe", "libpython", "uvicorn")), "Python/backend runtime packaged"
            data = archive.read(name)
            if name.endswith(".dex"):
                all_strings.extend(dex_strings(data))
            elif name.startswith("assets/"):
                all_strings.append(data.decode("utf-8", errors="replace"))
        for filename in ("ziwei.html", "ziwei.css", "ziwei.js"):
            assert archive.read(f"assets/{filename}") == (ROOT / "app/static" / filename).read_bytes(), f"stale UI asset: {filename}"
    combined = "\n".join(all_strings)
    for required in ("Lcom/tiger/ziwei/core/TigerCalendar;", "Lcom/tiger/ziwei/core/ZiweiCore;", "Lcom/tiger/ziwei/core/DocxReport;", "Lcom/nlf/calendar/Lunar;", "Lcom/tiger/ziwei/MainActivity;", "https://integrate.api.nvidia.com/v1/chat/completions", "https://appassets.androidplatform.net"):
        assert required in combined, f"missing native component: {required}"
    for forbidden in ("10.0.2.2", "127.0.0.1:18080", "Server URL", "server_url", "/health", "FastAPI URL", "connectToServer", "showServerSetup", "uvicorn", "mock-unused-key", "transient-browser-key"):
        assert forbidden not in combined, f"forbidden backend/test artifact: {forbidden}"
    assert not re.search(r"nvapi-[A-Za-z0-9_-]{8,}", combined), "possible NVIDIA secret packaged"
    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("NVIDIA_API_KEY="):
                value = line.partition("=")[2].strip().strip("\"'")
                if len(value) >= 8:
                    assert value not in combined, "configured secret packaged"
    print(json.dumps({
        "status": "PASS", "apk": str(path), "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        "entries": len(entries), "structure": "PASS", "local_ui_assets": "PASS",
        "calendar_core_classes": "PASS", "secret_scan": "PASS", "backend_dependency_scan": "PASS",
        "native_https_endpoint": "PASS", "device_runtime": "USER REQUIRED",
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
